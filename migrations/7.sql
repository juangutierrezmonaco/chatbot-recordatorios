-- Migration 7: add_admin_mode_fields
-- Created: 2025-09-23T17:30:00.000000

-- Add admin mode fields to users table
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN admin_activated_at TEXT DEFAULT NULL;