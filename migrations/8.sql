-- Migration 8: create_secret_gallery_table
-- Created: 2025-09-23T17:45:00.000000

-- Create secret gallery table to store photos/memes for surprise command
CREATE TABLE IF NOT EXISTS secret_gallery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT NOT NULL,              -- Telegram file_id for the photo/document
    file_type TEXT NOT NULL,            -- 'photo', 'document', 'sticker', etc.
    original_filename TEXT,             -- Original filename if available
    description TEXT,                   -- Optional description from admin
    uploaded_by INTEGER NOT NULL,      -- chat_id of the admin who uploaded
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE     -- For soft delete functionality
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_secret_gallery_active ON secret_gallery(is_active);
CREATE INDEX IF NOT EXISTS idx_secret_gallery_type ON secret_gallery(file_type);