from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import logging
from datetime import datetime
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

def load_pending_reminders(bot: Bot):
    """Load all pending reminders when restarting the bot."""
    reminders = db.get_all_active_reminders()
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

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
        else:
            # Mark as expired if the date has already passed
            db.mark_reminder_sent(reminder['id'])
            logger.info(f"Reminder {reminder['id']} expired on restart")

    logger.info(f"Loaded {len(reminders)} pending reminders")

def shutdown_scheduler():
    """Stop the scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")