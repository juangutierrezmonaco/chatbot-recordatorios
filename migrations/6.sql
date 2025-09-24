-- Migration 6: add_girlfriend_mode_fields
-- Created: 2025-09-23T17:00:00.000000

-- Add girlfriend mode fields to users table
ALTER TABLE users ADD COLUMN is_girlfriend BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN girlfriend_activated_at TEXT DEFAULT NULL;