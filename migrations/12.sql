-- Migration 12: reset_special_modes
-- Created: 2026-11-13T22:00:00.000000

-- The admin password and the special mode phrase were in the public repository (issue #14).
-- Admins now come from the ADMIN_USER_IDS variable, so is_admin is no longer read, and the
-- special mode activated with the old phrase has to be activated again with the new one.
UPDATE users SET is_admin = FALSE, admin_activated_at = NULL;
UPDATE users SET is_girlfriend = FALSE, girlfriend_activated_at = NULL;
