-- Migration 11: create_app_state_table
-- Created: 2026-11-13T18:45:00.000000

-- Key/value store for bot-wide state that must survive restarts,
-- such as the last release announced to users
CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
