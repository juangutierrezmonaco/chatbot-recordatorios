"""Reminders that must not get lost: restarts, failed sends, cancelling (issues #6 and #7).

Run from the project root:
    python3 -m unittest discover -s tests -v
"""
import asyncio
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from apscheduler.triggers.date import DateTrigger
from telegram.error import Forbidden, NetworkError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import db  # noqa: E402
import scheduler  # noqa: E402
from migrations import MigrationManager  # noqa: E402

CHAT = 1


class FakeScheduler:
    """Keeps jobs by id like a running APScheduler, so tests can inspect and run them."""

    def __init__(self):
        self.jobs = {}

    def add_job(self, func, trigger, args=(), kwargs=None, id=None, replace_existing=False, **options):
        if id in self.jobs and not replace_existing:
            raise ValueError(f'Job {id} already exists')
        self.jobs[id] = SimpleNamespace(func=func, trigger=trigger, args=list(args), kwargs=kwargs or {})

    def remove_job(self, job_id):
        if job_id not in self.jobs:
            raise LookupError(job_id)
        del self.jobs[job_id]


class FakeBot:
    def __init__(self, error=None):
        self.sent = []
        self.error = error

    async def send_message(self, chat_id, text, parse_mode=None, **kwargs):
        if self.error:
            raise self.error
        self.sent.append(SimpleNamespace(chat_id=chat_id, text=text, parse_mode=parse_mode))


def now():
    return datetime.now(scheduler.TIMEZONE)


class SchedulerTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tmp_dir.name, 'test.db')
        MigrationManager(db.DB_PATH, migrations_dir=os.path.join(ROOT, 'migrations')).run_migrations()

        self.original_scheduler = scheduler.scheduler
        self.jobs = FakeScheduler()
        scheduler.scheduler = self.jobs
        self.bot = FakeBot()

    def tearDown(self):
        scheduler.scheduler = self.original_scheduler
        db.DB_PATH = self.original_db_path
        self.tmp_dir.cleanup()

    def regular(self, when, text='Comprar pan'):
        return db.add_reminder(CHAT, text, when)

    def important(self, when, interval=10, text='Tomar la pastilla', last_sent=None, times_sent=0):
        reminder_id = db.add_important_reminder(CHAT, text, when, repeat_interval=interval)
        with sqlite3.connect(db.DB_PATH) as conn:
            conn.execute(
                'UPDATE reminders SET last_sent = ?, times_sent = ? WHERE id = ?',
                (last_sent, times_sent, reminder_id)
            )
        return reminder_id

    def status(self, reminder_id):
        with sqlite3.connect(db.DB_PATH) as conn:
            return conn.execute('SELECT status FROM reminders WHERE id = ?', (reminder_id,)).fetchone()[0]

    def times_sent(self, reminder_id):
        with sqlite3.connect(db.DB_PATH) as conn:
            return conn.execute('SELECT times_sent FROM reminders WHERE id = ?', (reminder_id,)).fetchone()[0]

    def run_job(self, job_id, bot=None):
        job = self.jobs.jobs[job_id]
        # Like APScheduler, a one-off job is gone once it runs
        if isinstance(job.trigger, DateTrigger):
            del self.jobs.jobs[job_id]
        if bot is not None:
            job.args[0] = bot
        asyncio.run(job.func(*job.args, **job.kwargs))

    def assertAround(self, moment, expected, seconds=10):
        self.assertLess(abs((moment - expected).total_seconds()), seconds, f'{moment} is not near {expected}')


class LoadOnStartup(SchedulerTestCase):
    def test_future_regular_reminder_keeps_its_time(self):
        when = now() + timedelta(hours=2)
        reminder_id = self.regular(when)

        scheduler.load_pending_reminders(self.bot)

        job = self.jobs.jobs[f'reminder_{reminder_id}']
        self.assertAround(job.trigger.run_date, when, seconds=1)

    def test_regular_reminder_due_during_the_downtime_is_sent_late(self):
        due = now() - timedelta(minutes=30)
        reminder_id = self.regular(due)

        scheduler.load_pending_reminders(self.bot)
        job = self.jobs.jobs[f'reminder_{reminder_id}']
        self.assertAround(job.trigger.run_date, now() + scheduler.STARTUP_DELAY)

        self.run_job(f'reminder_{reminder_id}', self.bot)
        self.assertIn('Comprar pan', self.bot.sent[0].text)
        self.assertIn('Llega con demora', self.bot.sent[0].text)
        self.assertEqual(self.status(reminder_id), 'sent')

    def test_an_important_reminder_gets_a_single_job(self):
        reminder_id = self.important(now() + timedelta(hours=1))

        scheduler.load_pending_reminders(self.bot)

        self.assertEqual(list(self.jobs.jobs), [f'important_reminder_{reminder_id}'])

    def test_important_reminder_never_sent_starts_right_away(self):
        reminder_id = self.important(now() - timedelta(minutes=30))

        scheduler.load_pending_reminders(self.bot)

        trigger = self.jobs.jobs[f'important_reminder_{reminder_id}'].trigger
        self.assertAround(trigger.start_date, now() + scheduler.STARTUP_DELAY)

    def test_important_reminder_already_repeating_continues_from_its_last_message(self):
        last_sent = now() - timedelta(minutes=3)
        reminder_id = self.important(now() - timedelta(hours=1), interval=10, last_sent=last_sent.isoformat())

        scheduler.load_pending_reminders(self.bot)

        trigger = self.jobs.jobs[f'important_reminder_{reminder_id}'].trigger
        self.assertAround(trigger.start_date, last_sent + timedelta(minutes=10), seconds=1)
        self.assertEqual(trigger.interval, timedelta(minutes=10))

    def test_old_last_sent_without_timezone_does_not_break_the_startup(self):
        naive_last_sent = datetime.now() - timedelta(minutes=30)
        reminder_id = self.important(now() - timedelta(hours=1), interval=10,
                                     last_sent=naive_last_sent.isoformat())

        scheduler.load_pending_reminders(self.bot)

        self.assertIn(f'important_reminder_{reminder_id}', self.jobs.jobs)

    def test_finished_reminders_are_not_loaded(self):
        sent_id = self.regular(now() + timedelta(hours=1))
        db.mark_reminder_sent(sent_id)
        cancelled_id = self.important(now() + timedelta(hours=1))
        db.cancel_reminder(CHAT, cancelled_id)

        scheduler.load_pending_reminders(self.bot)

        self.assertEqual(self.jobs.jobs, {})


class SendRegularReminder(SchedulerTestCase):
    def schedule_and_run(self, reminder_id, due, bot):
        scheduler.schedule_reminder(self.bot, CHAT, reminder_id, 'Comprar pan', due)
        self.run_job(f'reminder_{reminder_id}', bot)

    def test_on_time_has_no_delay_notice(self):
        due = now()
        reminder_id = self.regular(due)
        self.schedule_and_run(reminder_id, due, self.bot)

        self.assertEqual(self.bot.sent[0].text, f'⏰ Recordatorio (#{reminder_id}): Comprar pan')
        self.assertEqual(self.status(reminder_id), 'sent')

    def test_a_date_without_timezone_is_read_as_buenos_aires_time(self):
        naive_due = datetime.now(scheduler.TIMEZONE).replace(tzinfo=None) - timedelta(minutes=10)
        reminder_id = self.regular(naive_due)
        self.schedule_and_run(reminder_id, naive_due, self.bot)

        self.assertIn('Llega con demora', self.bot.sent[0].text)
        self.assertEqual(self.status(reminder_id), 'sent')

    def test_a_cancelled_reminder_is_not_sent(self):
        due = now()
        reminder_id = self.regular(due)
        scheduler.schedule_reminder(self.bot, CHAT, reminder_id, 'Comprar pan', due)
        db.cancel_reminder(CHAT, reminder_id)

        self.run_job(f'reminder_{reminder_id}', self.bot)

        self.assertEqual(self.bot.sent, [])
        self.assertEqual(self.status(reminder_id), 'cancelled')

    def test_blocked_bot_marks_it_failed_without_retrying(self):
        due = now()
        reminder_id = self.regular(due)
        self.schedule_and_run(reminder_id, due, FakeBot(Forbidden('bot was blocked by the user')))

        self.assertEqual(self.status(reminder_id), 'failed')
        self.assertNotIn(f'reminder_{reminder_id}', self.jobs.jobs)

    def test_network_errors_are_retried_and_then_marked_failed(self):
        due = now()
        reminder_id = self.regular(due)
        failing = FakeBot(NetworkError('Telegram is down'))
        self.schedule_and_run(reminder_id, due, failing)

        for attempt, delay in enumerate(scheduler.RETRY_DELAYS, start=1):
            job = self.jobs.jobs[f'reminder_{reminder_id}']
            self.assertEqual(job.kwargs['attempt'], attempt)
            self.assertAround(job.trigger.run_date, now() + delay)
            self.assertEqual(self.status(reminder_id), 'active')
            self.run_job(f'reminder_{reminder_id}', failing)

        self.assertEqual(self.status(reminder_id), 'failed')

    def test_a_retry_that_works_marks_it_sent(self):
        due = now()
        reminder_id = self.regular(due)
        self.schedule_and_run(reminder_id, due, FakeBot(NetworkError('Telegram is down')))

        self.run_job(f'reminder_{reminder_id}', self.bot)

        self.assertEqual(self.status(reminder_id), 'sent')
        self.assertEqual(len(self.bot.sent), 1)


class SendImportantReminder(SchedulerTestCase):
    def schedule(self, reminder_id, start=None):
        scheduler.schedule_important_reminder(reminder_id, start or now(), 10, self.bot)
        return f'important_reminder_{reminder_id}'

    def test_each_message_is_counted_and_the_text_is_escaped(self):
        reminder_id = self.important(now(), text='Pagar <luz> & gas')
        job_id = self.schedule(reminder_id)

        self.run_job(job_id, self.bot)
        self.run_job(job_id, self.bot)

        self.assertEqual(self.times_sent(reminder_id), 2)
        self.assertEqual(self.bot.sent[0].parse_mode, 'HTML')
        self.assertIn('Pagar &lt;luz&gt; &amp; gas', self.bot.sent[0].text)
        self.assertIn(f'/completar {reminder_id}', self.bot.sent[0].text)
        self.assertEqual(self.status(reminder_id), 'active')

    def test_stops_after_the_last_repetition_and_says_so(self):
        reminder_id = self.important(now() - timedelta(hours=8),
                                     last_sent=now().isoformat(),
                                     times_sent=scheduler.MAX_IMPORTANT_REPETITIONS - 1)
        job_id = self.schedule(reminder_id)

        self.run_job(job_id, self.bot)

        self.assertIn('dejo de insistir', self.bot.sent[0].text)
        self.assertIn(f'/repetir {reminder_id}', self.bot.sent[0].text)
        self.assertEqual(self.status(reminder_id), 'sent')
        self.assertNotIn(job_id, self.jobs.jobs)

    def test_a_start_without_timezone_is_read_as_buenos_aires_time(self):
        naive_start = datetime.now(scheduler.TIMEZONE).replace(tzinfo=None) + timedelta(hours=1)
        reminder_id = self.important(naive_start)
        trigger = self.jobs.jobs[self.schedule(reminder_id, start=naive_start)].trigger
        self.assertAround(trigger.start_date, scheduler.TIMEZONE.localize(naive_start), seconds=1)

    def test_first_message_after_a_downtime_says_it_is_late(self):
        reminder_id = self.important(now() - timedelta(minutes=30))
        self.run_job(self.schedule(reminder_id), self.bot)
        self.assertIn('Llega con demora', self.bot.sent[0].text)

    def test_cancelled_while_repeating_stops_the_job(self):
        reminder_id = self.important(now())
        job_id = self.schedule(reminder_id)
        db.cancel_reminder(CHAT, reminder_id)

        self.run_job(job_id, self.bot)

        self.assertEqual(self.bot.sent, [])
        self.assertNotIn(job_id, self.jobs.jobs)

    def test_blocked_bot_stops_the_repetition(self):
        reminder_id = self.important(now())
        job_id = self.schedule(reminder_id)

        self.run_job(job_id, FakeBot(Forbidden('bot was blocked by the user')))

        self.assertEqual(self.status(reminder_id), 'failed')
        self.assertNotIn(job_id, self.jobs.jobs)

    def test_network_error_waits_for_the_next_repetition(self):
        reminder_id = self.important(now())
        job_id = self.schedule(reminder_id)

        self.run_job(job_id, FakeBot(NetworkError('Telegram is down')))

        self.assertEqual(self.status(reminder_id), 'active')
        self.assertEqual(self.times_sent(reminder_id), 0)
        self.assertIn(job_id, self.jobs.jobs)


class CancelAndComplete(SchedulerTestCase):
    def test_cancelling_removes_the_job_of_an_important_reminder(self):
        reminder_id = self.important(now() + timedelta(hours=1))
        scheduler.load_pending_reminders(self.bot)

        self.assertTrue(scheduler.cancel_reminder(reminder_id))
        self.assertEqual(self.jobs.jobs, {})
        self.assertFalse(scheduler.cancel_reminder(reminder_id))

    def test_cancelling_several_reminders_of_both_kinds(self):
        ids = [self.regular(now() + timedelta(hours=1)), self.important(now() + timedelta(hours=1))]
        scheduler.load_pending_reminders(self.bot)

        scheduler.cancel_reminders(ids)

        self.assertEqual(self.jobs.jobs, {})

    def test_complete_works_for_regular_and_important_reminders(self):
        regular_id = self.regular(now() + timedelta(hours=1))
        important_id = self.important(now() + timedelta(hours=1))

        self.assertTrue(db.complete_reminder(CHAT, regular_id))
        self.assertTrue(db.complete_reminder(CHAT, important_id))
        self.assertFalse(db.complete_reminder(CHAT, regular_id), 'no longer active')
        self.assertFalse(db.complete_reminder(CHAT + 1, important_id), 'another chat')
        self.assertEqual(self.status(regular_id), 'completed')

    def test_a_cancelled_reminder_is_never_marked_sent(self):
        reminder_id = self.regular(now())
        db.cancel_reminder(CHAT, reminder_id)
        self.assertFalse(db.mark_reminder_sent(reminder_id))
        self.assertEqual(self.status(reminder_id), 'cancelled')


class MissedDailySummary(SchedulerTestCase):
    def at(self, hour, minute=0):
        return scheduler.TIMEZONE.localize(datetime(2026, 11, 14, hour, minute))

    def test_missed_only_after_summary_time_and_before_midnight(self):
        self.assertTrue(scheduler.summary_missed_tonight(self.at(22, 30), '2026-11-13'))
        self.assertTrue(scheduler.summary_missed_tonight(self.at(23, 59), '2026-11-13'))
        self.assertFalse(scheduler.summary_missed_tonight(self.at(21, 59), '2026-11-13'))
        self.assertFalse(scheduler.summary_missed_tonight(self.at(22, 30), '2026-11-14'), 'already sent')
        self.assertFalse(scheduler.summary_missed_tonight(self.at(22, 30), None), 'nothing recorded yet')

    def test_sending_the_summary_records_the_night(self):
        db.add_reminder(CHAT, 'Dentista', now() + timedelta(days=1))
        night = self.at(22, 40)

        asyncio.run(scheduler.send_daily_summary(self.bot, night=night))

        self.assertEqual(len(self.bot.sent), 1)
        self.assertEqual(db.get_app_state(scheduler.LAST_DAILY_SUMMARY_KEY), '2026-11-14')

    def test_a_summary_that_reached_nobody_is_not_recorded(self):
        db.add_reminder(CHAT, 'Dentista', now() + timedelta(days=1))
        asyncio.run(scheduler.send_daily_summary(FakeBot(NetworkError('down')), night=now()))
        self.assertIsNone(db.get_app_state(scheduler.LAST_DAILY_SUMMARY_KEY))

    def test_startup_after_a_missed_summary_sends_it(self):
        db.set_app_state(scheduler.LAST_DAILY_SUMMARY_KEY, '2000-01-01')
        scheduler.schedule_daily_summary(self.bot)

        missed = scheduler.summary_missed_tonight(now(), '2000-01-01')
        self.assertEqual(scheduler.DAILY_SUMMARY_CATCH_UP_JOB_ID in self.jobs.jobs, missed)
        self.assertIn(scheduler.DAILY_SUMMARY_JOB_ID, self.jobs.jobs)


if __name__ == '__main__':
    unittest.main()
