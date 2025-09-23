from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging
from datetime import datetime, timedelta
import pytz
from telegram import Bot
import db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=pytz.timezone('America/Argentina/Buenos_Aires'))

def init_scheduler():
    """Initialize the scheduler."""
    scheduler.start()
    logger.info("Scheduler started")

async def send_reminder(bot: Bot, chat_id: int, reminder_id: int, text: str):
    """Send a reminder to the user and mark as sent in DB."""
    try:
        message = f"⏰ Recordatorio (#{reminder_id}): {text}"
        await bot.send_message(chat_id=chat_id, text=message)
        db.mark_reminder_sent(reminder_id)
        logger.info(f"Reminder {reminder_id} sent to chat {chat_id}")
    except Exception as e:
        logger.error(f"Error sending reminder {reminder_id}: {e}")

async def send_important_reminder(bot: Bot, chat_id: int, reminder_id: int, text: str, repeat_interval: int):
    """Send an important reminder and update last_sent timestamp."""
    try:
        message = f"🔥 **RECORDATORIO IMPORTANTE** (#{reminder_id}):\n{text}\n\n💡 Usa `/completar {reminder_id}` para detener la repetición."
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        db.update_reminder_last_sent(reminder_id)
        logger.info(f"Important reminder {reminder_id} sent to chat {chat_id} (repeat every {repeat_interval}min)")
    except Exception as e:
        logger.error(f"Error sending important reminder {reminder_id}: {e}")

def schedule_reminder(bot: Bot, chat_id: int, reminder_id: int, text: str, datetime_obj: datetime):
    """Schedule a reminder in the scheduler."""
    job_id = f"reminder_{reminder_id}"

    scheduler.add_job(
        send_reminder,
        trigger=DateTrigger(run_date=datetime_obj),
        args=[bot, chat_id, reminder_id, text],
        id=job_id,
        name=f"Recordatorio #{reminder_id}",
        misfire_grace_time=60
    )

    logger.info(f"Reminder {reminder_id} scheduled for {datetime_obj}")

def schedule_important_reminder(reminder_id: int, datetime_obj: datetime, repeat_interval: int, bot: Bot):
    """Schedule an important reminder that repeats every X minutes after the initial time."""
    job_id = f"important_reminder_{reminder_id}"

    # Get reminder details
    reminders = db.get_active_important_reminders()
    reminder = next((r for r in reminders if r['id'] == reminder_id), None)

    if not reminder:
        logger.error(f"Important reminder {reminder_id} not found")
        return

    chat_id = reminder['chat_id']
    text = reminder['text']

    # Schedule the repeating job starting from the specified datetime
    scheduler.add_job(
        send_important_reminder,
        trigger=IntervalTrigger(
            minutes=repeat_interval,
            start_date=datetime_obj
        ),
        args=[bot, chat_id, reminder_id, text, repeat_interval],
        id=job_id,
        name=f"Important Reminder #{reminder_id} (every {repeat_interval}min)",
        misfire_grace_time=60
    )

    logger.info(f"Important reminder {reminder_id} scheduled to start at {datetime_obj} and repeat every {repeat_interval} minutes")

def cancel_reminder(reminder_id: int):
    """Cancel both regular and important reminder jobs."""
    regular_job_id = f"reminder_{reminder_id}"
    important_job_id = f"important_reminder_{reminder_id}"

    cancelled_jobs = []

    # Try to cancel regular reminder
    try:
        scheduler.remove_job(regular_job_id)
        cancelled_jobs.append(regular_job_id)
        logger.info(f"Regular job {regular_job_id} cancelled")
    except Exception as e:
        logger.debug(f"Could not cancel regular job {regular_job_id}: {e}")

    # Try to cancel important reminder
    try:
        scheduler.remove_job(important_job_id)
        cancelled_jobs.append(important_job_id)
        logger.info(f"Important job {important_job_id} cancelled")
    except Exception as e:
        logger.debug(f"Could not cancel important job {important_job_id}: {e}")

    return len(cancelled_jobs) > 0

def cancel_reminder_job(reminder_id: int):
    """Cancel a job from the scheduler."""
    job_id = f"reminder_{reminder_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Job {job_id} cancelled")
        return True
    except Exception as e:
        logger.warning(f"Could not cancel job {job_id}: {e}")
        return False

def cancel_multiple_reminder_jobs(reminder_ids: list) -> dict:
    """Cancel multiple jobs from the scheduler."""
    cancelled = []
    failed = []

    for reminder_id in reminder_ids:
        if cancel_reminder_job(reminder_id):
            cancelled.append(reminder_id)
        else:
            failed.append(reminder_id)

    return {"cancelled": cancelled, "failed": failed}

def load_pending_reminders(bot: Bot):
    """Load all pending reminders when restarting the bot."""
    # Load regular reminders
    reminders = db.get_all_active_reminders()
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

    regular_count = 0
    for reminder in reminders:
        datetime_obj = reminder['datetime']

        # Only schedule if the date is in the future
        if datetime_obj > now:
            schedule_reminder(
                bot,
                reminder['chat_id'],
                reminder['id'],
                reminder['text'],
                datetime_obj
            )
            regular_count += 1
        else:
            # Mark as expired if the date has already passed
            db.mark_reminder_sent(reminder['id'])
            logger.info(f"Reminder {reminder['id']} expired on restart")

    # Load important reminders
    important_reminders = db.get_active_important_reminders()
    important_count = 0

    for reminder in important_reminders:
        datetime_obj = reminder['datetime']
        repeat_interval = reminder['repeat_interval']

        # Check if reminder time has passed but hasn't been sent yet
        if datetime_obj <= now:
            # If last_sent is None or the repeat interval has passed since last_sent
            last_sent = reminder['last_sent']
            should_schedule = False

            if last_sent is None:
                # Never sent, schedule to start immediately
                should_schedule = True
                datetime_obj = now + timedelta(seconds=5)  # Start in 5 seconds
            else:
                # Check if enough time has passed since last sent
                time_since_last = now - last_sent
                if time_since_last >= timedelta(minutes=repeat_interval):
                    should_schedule = True
                    datetime_obj = now + timedelta(seconds=5)  # Start in 5 seconds

            if should_schedule:
                schedule_important_reminder(reminder['id'], datetime_obj, repeat_interval, bot)
                important_count += 1
        else:
            # Future reminder, schedule normally
            schedule_important_reminder(reminder['id'], datetime_obj, repeat_interval, bot)
            important_count += 1

    logger.info(f"Loaded {regular_count} regular reminders and {important_count} important reminders")

def shutdown_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")