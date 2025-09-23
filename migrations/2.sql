-- Migration 2: create_users_table
-- Created: 2025-09-23T12:30:00.000000

-- Create users table for chat isolation and user management
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_bot INTEGER DEFAULT 0,
    language_code TEXT DEFAULT 'es',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for better performance on chat_id lookups
CREATE INDEX IF NOT EXISTS idx_users_chat_id ON users(chat_id);
CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);