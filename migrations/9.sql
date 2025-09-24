-- Migration 9: update_secret_gallery_for_local_files
-- Created: 2025-09-24T11:40:00.000000

-- Add local file path column and update schema for local file storage
ALTER TABLE secret_gallery ADD COLUMN local_file_path TEXT;

-- We'll keep file_id for backward compatibility but prioritize local_file_path
-- Mark old file_id entries as inactive since they're problematic
UPDATE secret_gallery SET is_active = FALSE WHERE local_file_path IS NULL;