-- Migration 4: add_vault_status_field
-- Created: 2025-09-23T15:30:00.000000

-- Add status field to vault table for history functionality
ALTER TABLE vault ADD COLUMN status TEXT DEFAULT 'active';

-- Add deleted_at field to track when entries were deleted
ALTER TABLE vault ADD COLUMN deleted_at TEXT;

-- Create index for better performance on status searches
CREATE INDEX IF NOT EXISTS idx_vault_status ON vault(status);