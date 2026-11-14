from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import html
import logging
from datetime import datetime, time, timedelta
from typing import Optional
import pytz
from telegram import Bot
from telegram.error import BadRequest, Forbidden
import db

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone('America/Argentina/Buenos_Aires')

scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# Nightly summary of the next day's reminders
DAILY_SUMMARY_HOUR = 22
DAILY_SUMMARY_MINUTE = 0
DAILY_SUMMARY_JOB_ID = "daily_summary"
DAILY_SUMMARY_CATCH_UP_JOB_ID = "daily_summary_catch_up"
LAST_DAILY_SUMMARY_KEY = "last_daily_summary"

WEEKDAYS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
             'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

# Jobs live in memory: on startup they are rebuilt from the database, where a reminder
# stays 'active' until it is delivered ('sent'), given up ('failed'), cancelled or completed.

# Waits before trying again when Telegram or the network fail; then the reminder is 'failed'
RETRY_DELAYS = [timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15)]

# A reminder that arrives later than this says so (the bot was down, or busy)
LATE_NOTICE_AFTER = timedelta(minutes=2)

# An important reminder stops insisting after this many messages
MAX_IMPORTANT_REPETITIONS = 50

# Reminders due while the bot was down go out right after startup, a little apart
STARTUP_DELAY = timedelta(seconds=5)
SECONDS_BETWEEN_LATE_REMINDERS = 1

# Telegram errors that will not go away by trying again: the user blocked the bot,
# the chat no longer exists, or the message itself is invalid
PERMANENT_SEND_ERRORS = (Forbidden, BadRequest)

def init_scheduler():
    """Initialize the scheduler."""
    scheduler.start()
    logger.info("Scheduler started")

def _now() -> datetime:
    return datetime.now(TIMEZONE)

def _aware(moment: datetime) -> datetime:
    """Dates without a timezone (older reminders) are Buenos Aires time."""
    return TIMEZONE.localize(moment) if moment.tzinfo is None else moment

def _regular_job_id(reminder_id: int) -> str:
    return f"reminder_{reminder_id}"

def _important_job_id(reminder_id: int) -> str:
    return f"important_reminder_{reminder_id}"

def _remove_job(job_id: str) -> bool:
    try:
        scheduler.remove_job(job_id)
        return True
    except Exception:
        return False

def _late_notice(due: Optional[datetime], now: datetime) -> str:
    """'Llega con demora' line when the reminder is late, else empty."""
    if due is None or now - due <= LATE_NOTICE_AFTER:
        return ""
    return f"\n\n🕐 Llega con demora: era para el {due.astimezone(TIMEZONE).strftime('%d/%m a las %H:%M')}."

async def send_reminder(bot: Bot, chat_id: int, reminder_id: int, text: str,
                        due: Optional[datetime] = None, attempt: int = 0):
    """Send a regular reminder; retry if Telegram or the network fail."""
    if db.get_active_reminder(reminder_id) is None:
        logger.info(f"Reminder {reminder_id} is no longer active; not sending it")
        return

    message = f"⏰ Recordatorio (#{reminder_id}): {text}{_late_notice(due, _now())}"
    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except PERMANENT_SEND_ERRORS as error:
        logger.error(f"Reminder {reminder_id} cannot be delivered to chat {chat_id}: {error}")
        db.mark_reminder_failed(reminder_id)
        return
    except Exception as error:
        if attempt >= len(RETRY_DELAYS):
            logger.error(f"Reminder {reminder_id} failed after {attempt + 1} attempts: {error}")
            db.mark_reminder_failed(reminder_id)
            return

        retry_at = _now() + RETRY_DELAYS[attempt]
        logger.warning(f"Error sending reminder {reminder_id} ({error}); retrying at {retry_at}")
        _add_regular_job(bot, chat_id, reminder_id, text, retry_at, due, attempt + 1)
        return

    db.mark_reminder_sent(reminder_id)
    logger.info(f"Reminder {reminder_id} sent to chat {chat_id}")

def _important_message(reminder_id: int, text: str, times_sent: int, late_notice: str) -> str:
    """HTML message: the text is escaped so any character reaches the user."""
    message = f"🔥 <b>RECORDATORIO IMPORTANTE</b> (#{reminder_id}):\n{html.escape(text)}{late_notice}\n\n"
    if times_sent + 1 >= MAX_IMPORTANT_REPETITIONS:
        return message + (
            f"🛑 Es el aviso número {MAX_IMPORTANT_REPETITIONS}: dejo de insistir. "
            f"Si todavía lo necesitás, usá /repetir {reminder_id} con una fecha nueva."
        )
    return message + f"💡 Usá /completar {reminder_id} para detener la repetición."

async def send_important_reminder(bot: Bot, chat_id: int, reminder_id: int, text: str, repeat_interval: int):
    """Send one repetition of an important reminder; stop at MAX_IMPORTANT_REPETITIONS."""
    reminder = db.get_active_reminder(reminder_id)
    if reminder is None:
        logger.info(f"Important reminder {reminder_id} is no longer active; stopping its repetition")
        _remove_job(_important_job_id(reminder_id))
        return

    times_sent = reminder['times_sent']
    late_notice = _late_notice(reminder['datetime'], _now()) if reminder['last_sent'] is None else ""
    message = _important_message(reminder_id, text, times_sent, late_notice)

    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
    except PERMANENT_SEND_ERRORS as error:
        logger.error(f"Important reminder {reminder_id} cannot be delivered to chat {chat_id}: {error}")
        db.mark_reminder_failed(reminder_id)
        _remove_job(_important_job_id(reminder_id))
        return
    except Exception as error:
        # The next repetition tries again
        logger.warning(f"Error sending important reminder {reminder_id}: {error}")
        return

    db.record_important_reminder_sent(reminder_id)
    logger.info(f"Important reminder {reminder_id} sent to chat {chat_id} ({times_sent + 1}/{MAX_IMPORTANT_REPETITIONS})")

    if times_sent + 1 >= MAX_IMPORTANT_REPETITIONS:
        db.mark_reminder_sent(reminder_id)
        _remove_job(_important_job_id(reminder_id))
        logger.info(f"Important reminder {reminder_id} reached {MAX_IMPORTANT_REPETITIONS} repetitions")

def _add_regular_job(bot: Bot, chat_id: int, reminder_id: int, text: str, run_at: datetime,
                     due: datetime, attempt: int = 0):
    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=run_at),
        args=[bot, chat_id, reminder_id, text],
        kwargs={'due': due, 'attempt': attempt},
        id=_regular_job_id(reminder_id),
        name=f"Recordatorio #{reminder_id}",
        replace_existing=True,
        # Run however late it is (the bot was busy): never drop a reminder silently
        misfire_grace_time=None
    )

def schedule_reminder(bot: Bot, chat_id: int, reminder_id: int, text: str, datetime_obj: datetime,
                      run_at: Optional[datetime] = None):
    """Schedule a regular reminder due at datetime_obj (sent at run_at if given, for late ones)."""
    due = _aware(datetime_obj)
    _add_regular_job(bot, chat_id, reminder_id, text, _aware(run_at) if run_at else due, due)
    logger.info(f"Reminder {reminder_id} scheduled for {run_at or datetime_obj}")

def schedule_important_reminder(reminder_id: int, datetime_obj: datetime, repeat_interval: int, bot: Bot):
    """Schedule an important reminder that repeats every X minutes from datetime_obj.

    A start time already past (bot restarted) starts right away.
    """
    reminder = db.get_active_reminder(reminder_id)
    if not reminder or not reminder['is_important']:
        logger.error(f"Important reminder {reminder_id} not found")
        return

    start = max(_aware(datetime_obj), _now() + STARTUP_DELAY)
    scheduler.add_job(
        send_important_reminder,
        trigger=IntervalTrigger(minutes=repeat_interval, start_date=start),
        args=[bot, reminder['chat_id'], reminder_id, reminder['text'], repeat_interval],
        id=_important_job_id(reminder_id),
        name=f"Important Reminder #{reminder_id} (every {repeat_interval}min)",
        replace_existing=True,
        misfire_grace_time=None,
        # If several repetitions were missed while the bot was busy, send only one
        coalesce=True
    )

    logger.info(f"Important reminder {reminder_id} scheduled to start at {start} and repeat every {repeat_interval} minutes")

def cancel_reminder(reminder_id: int) -> bool:
    """Remove the scheduled job of a reminder, regular or important. False if it had none."""
    removed = [job_id for job_id in (_regular_job_id(reminder_id), _important_job_id(reminder_id))
               if _remove_job(job_id)]
    for job_id in removed:
        logger.info(f"Job {job_id} cancelled")
    return bool(removed)

def cancel_reminders(reminder_ids: list):
    """Remove the scheduled jobs of several reminders."""
    for reminder_id in reminder_ids:
        cancel_reminder(reminder_id)

def load_pending_reminders(bot: Bot):
    """Rebuild the jobs of every active reminder when the bot starts.

    Regular reminders due while the bot was down are sent right away, saying they are
    late. Important ones keep repeating from their last message.
    """
    now = _now()

    on_time = 0
    late = 0
    for reminder in db.get_all_active_reminders():
        if reminder['datetime'] > now:
            schedule_reminder(bot, reminder['chat_id'], reminder['id'], reminder['text'], reminder['datetime'])
            on_time += 1
        else:
            run_at = now + STARTUP_DELAY + timedelta(seconds=late * SECONDS_BETWEEN_LATE_REMINDERS)
            schedule_reminder(bot, reminder['chat_id'], reminder['id'], reminder['text'],
                              reminder['datetime'], run_at=run_at)
            late += 1

    important = db.get_active_important_reminders()
    for reminder in important:
        interval = timedelta(minutes=reminder['repeat_interval'])
        next_time = reminder['last_sent'] + interval if reminder['last_sent'] else reminder['datetime']
        schedule_important_reminder(reminder['id'], next_time, reminder['repeat_interval'], bot)

    logger.info(
        f"Loaded {on_time} regular reminders, {late} late ones to send now "
        f"and {len(important)} important reminders"
    )

def format_daily_summary(reminders: list, target_date: datetime, nightly: bool = True) -> str:
    """Build the tomorrow summary message (HTML) for a list of reminders.

    nightly=True is the automatic 22:00 message; False is the on-demand /manana reply.
    """
    date_label = f"{WEEKDAYS_ES[target_date.weekday()]} {target_date.day} de {MONTHS_ES[target_date.month - 1]}"
    count = len(reminders)
    count_label = "1 recordatorio" if count == 1 else f"{count} recordatorios"

    title = "🌙 <b>Resumen para mañana</b>" if nightly else "📅 <b>Tus recordatorios para mañana</b>"
    lines = [
        title,
        f"📅 {date_label.capitalize()} · {count_label}",
        "",
    ]

    for reminder in reminders:
        time_str = reminder['datetime'].astimezone(TIMEZONE).strftime("%H:%M")
        emoji = "🔥" if reminder.get('is_important') else "🔔"
        lines.append(f"{emoji} <b>{time_str}</b> · #{reminder['id']}")
        lines.append(f"   {html.escape(reminder['text'])}")
        lines.append("")

    if nightly:
        lines.append("💤 ¡Que descanses!")
    return "\n".join(lines).rstrip()

async def send_daily_summary(bot: Bot, night: Optional[datetime] = None):
    """Send each user a summary of their reminders scheduled for tomorrow.

    night is the evening the summary belongs to (now, unless it is a late catch-up).
    """
    night = night or _now()
    tomorrow = night + timedelta(days=1)

    try:
        reminders_by_chat = db.get_all_active_reminders_for_date(tomorrow)
    except Exception as e:
        logger.error(f"Error fetching reminders for daily summary: {e}")
        return

    sent = 0
    for chat_id, reminders in reminders_by_chat.items():
        try:
            message = format_daily_summary(reminders, tomorrow)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            sent += 1
        except Exception as e:
            logger.error(f"Error sending daily summary to chat {chat_id}: {e}")

    if sent or not reminders_by_chat:
        db.set_app_state(LAST_DAILY_SUMMARY_KEY, night.date().isoformat())
    logger.info(f"Daily summary sent to {sent}/{len(reminders_by_chat)} chats")

def summary_missed_tonight(now: datetime, last_summary_night: Optional[str]) -> bool:
    """The bot was down at summary time and it is still the same night.

    With no summary recorded yet (first start with this check) nothing is assumed missed,
    so a summary already sent tonight is not repeated.
    """
    summary_time = time(DAILY_SUMMARY_HOUR, DAILY_SUMMARY_MINUTE)
    return (
        last_summary_night is not None
        and now.time() >= summary_time
        and last_summary_night != now.date().isoformat()
    )

def schedule_daily_summary(bot: Bot):
    """Schedule the nightly job that sends tomorrow's reminders summary.

    If the bot starts after summary time and tonight's summary was not sent, it goes out now.
    """
    scheduler.add_job(
        send_daily_summary,
        trigger=CronTrigger(hour=DAILY_SUMMARY_HOUR, minute=DAILY_SUMMARY_MINUTE, timezone=TIMEZONE),
        args=[bot],
        id=DAILY_SUMMARY_JOB_ID,
        name="Resumen diario de recordatorios",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True
    )
    logger.info(f"Daily summary scheduled every day at {DAILY_SUMMARY_HOUR:02d}:{DAILY_SUMMARY_MINUTE:02d}")

    now = _now()
    if summary_missed_tonight(now, db.get_app_state(LAST_DAILY_SUMMARY_KEY)):
        scheduler.add_job(
            send_daily_summary,
            trigger=DateTrigger(run_date=now + STARTUP_DELAY),
            args=[bot],
            kwargs={'night': now},
            id=DAILY_SUMMARY_CATCH_UP_JOB_ID,
            name="Resumen diario atrasado",
            replace_existing=True,
            misfire_grace_time=None
        )
        logger.info("Tonight's summary was missed while the bot was down; sending it now")

def shutdown_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")