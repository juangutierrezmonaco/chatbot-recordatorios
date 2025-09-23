-- Migration 3: add_category_fields
-- Created: 2025-09-23T13:00:00.000000

-- Add category field to reminders table
ALTER TABLE reminders ADD COLUMN category TEXT DEFAULT 'general';

-- Add category field to vault table (bitácora)
ALTER TABLE vault ADD COLUMN category TEXT DEFAULT 'general';

-- Create indexes for better performance on category searches
CREATE INDEX IF NOT EXISTS idx_reminders_category ON reminders(category);
CREATE INDEX IF NOT EXISTS idx_vault_category ON vault(category);