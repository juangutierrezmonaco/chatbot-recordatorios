-- Migration 13: add_girlfriend_requests
-- Created: 2026-11-13T22:30:00.000000

-- A right answer to /novia no longer turns the special mode on: it leaves a request that
-- an admin approves or rejects. 'pending' or 'rejected'; NULL when there is no request.
-- A rejected chat cannot ask again until an admin approves it.
ALTER TABLE users ADD COLUMN girlfriend_request TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN girlfriend_requested_at TEXT DEFAULT NULL;
