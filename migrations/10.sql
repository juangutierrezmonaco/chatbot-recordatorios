-- Migration 10: make_file_id_optional
-- Created: 2025-09-24T11:45:00.000000

-- Make file_id column optional since we're moving to local file storage
-- We need to recreate the table since SQLite doesn't support ALTER COLUMN

-- Create new table with updated schema
CREATE TABLE IF NOT EXISTS secret_gallery_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,                       -- Now optional
    file_type TEXT NOT NULL,
    original_filename TEXT,
    description TEXT,
    uploaded_by INTEGER NOT NULL,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    local_file_path TEXT               -- New column for local file storage
);

-- Copy existing data
INSERT INTO secret_gallery_new (id, file_id, file_type, original_filename, description, uploaded_by, uploaded_at, is_active, local_file_path)
SELECT id, file_id, file_type, original_filename, description, uploaded_by, uploaded_at, is_active, local_file_path
FROM secret_gallery;

-- Drop old table and rename new one
DROP TABLE secret_gallery;
ALTER TABLE secret_gallery_new RENAME TO secret_gallery;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_secret_gallery_active ON secret_gallery(is_active);
CREATE INDEX IF NOT EXISTS idx_secret_gallery_type ON secret_gallery(file_type);