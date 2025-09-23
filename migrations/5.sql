-- Migration 5: add_important_reminders_fields
-- Created: 2025-09-23T16:50:00.000000

-- Add is_important field to mark important reminders
ALTER TABLE reminders ADD COLUMN is_important BOOLEAN DEFAULT FALSE;

-- Add repeat_interval field to store repeat interval in minutes
ALTER TABLE reminders ADD COLUMN repeat_interval INTEGER DEFAULT NULL;

-- Add last_sent field to track when reminder was last sent
ALTER TABLE reminders ADD COLUMN last_sent TEXT DEFAULT NULL;

-- Create index for better performance on important reminders
CREATE INDEX IF NOT EXISTS idx_reminders_important ON reminders(is_important);