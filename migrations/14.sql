-- Migration 14: add_reminder_times_sent
-- Created: 2026-11-14T10:00:00.000000

-- How many times an important reminder was sent: it stops insisting after a limit
-- (scheduler.MAX_IMPORTANT_REPETITIONS). A reminder that could not be delivered gets
-- status 'failed' (no schema change: status is free text).
ALTER TABLE reminders ADD COLUMN times_sent INTEGER DEFAULT 0;
