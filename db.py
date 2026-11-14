import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import unicodedata
import pytz
from migrations import MigrationManager

logger = logging.getLogger(__name__)

BUENOS_AIRES = pytz.timezone('America/Argentina/Buenos_Aires')

import os

# Use different paths for development vs production
if os.path.exists('/app/data'):  # Production in Fly.io
    DB_PATH = "/app/data/reminders.db"
    GALLERY_PATH = "/app/data/secret_gallery"
else:  # Local development
    DB_PATH = "database/reminders.db"
    GALLERY_PATH = "secret_gallery"

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(GALLERY_PATH, exist_ok=True)

def init_db():
    """Initialize the database and run migrations."""
    # Run migrations first
    migration_manager = MigrationManager(DB_PATH)
    success = migration_manager.run_migrations()

    if success:
        logger.info("Database initialized with migrations")
    else:
        logger.error("Database migration failed")
        # Fallback to old schema creation
        _create_legacy_schema()

def _create_legacy_schema():
    """Fallback schema creation if migrations fail."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            datetime TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Legacy database schema created")

def add_reminder(chat_id: int, text: str, datetime_obj: datetime, category: str = 'general') -> int:
    """Add a new reminder to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO reminders (chat_id, text, datetime, status, category)
        VALUES (?, ?, ?, ?, ?)
    ''', (chat_id, text, datetime_obj.isoformat(), 'active', category))

    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Reminder {reminder_id} added for chat {chat_id} with category '{category}'")
    return reminder_id

def get_active_reminders(chat_id: int) -> List[Dict]:
    """Get all active reminders for a chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime, category, is_important, repeat_interval
        FROM reminders
        WHERE chat_id = ? AND status = 'active'
        ORDER BY datetime
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        # Parse datetime and ensure it has timezone info
        dt = datetime.fromisoformat(row[2])
        if dt.tzinfo is None:
            # Assume Buenos Aires timezone for naive datetimes
            import pytz
            dt = pytz.timezone('America/Argentina/Buenos_Aires').localize(dt)

        reminders.append({
            'id': row[0],
            'text': row[1],
            'datetime': dt,
            'category': row[3] if len(row) > 3 and row[3] else 'general',
            'is_important': bool(row[4]) if len(row) > 4 and row[4] is not None else False,
            'repeat_interval': row[5] if len(row) > 5 and row[5] is not None else None
        })

    return reminders

# What a day shows (/hoy, /dia, /semana todos): cancelled reminders only appear in /historial
def _reminder_with_status(row) -> Dict:
    """Row: id, text, datetime, status, is_important, repeat_interval."""
    return {
        'id': row[0],
        'text': row[1],
        'datetime': _aware(row[2]),
        'status': row[3],
        'is_important': bool(row[4]),
        'repeat_interval': row[5]
    }

def _reminders_between(chat_id: int, start: datetime, end: datetime, only_active: bool) -> List[Dict]:
    """Reminders of a chat from start to end; all but cancelled ones, or only active ones."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if only_active:
        cursor.execute('''
            SELECT id, text, datetime, status, is_important, repeat_interval
            FROM reminders
            WHERE chat_id = ? AND status = 'active'
            AND datetime >= ? AND datetime <= ?
            ORDER BY datetime
        ''', (chat_id, start.isoformat(), end.isoformat()))
    else:
        cursor.execute('''
            SELECT id, text, datetime, status, is_important, repeat_interval
            FROM reminders
            WHERE chat_id = ? AND status IN ('active', 'sent', 'completed', 'failed')
            AND datetime >= ? AND datetime <= ?
            ORDER BY datetime
        ''', (chat_id, start.isoformat(), end.isoformat()))

    rows = cursor.fetchall()
    conn.close()

    return [_reminder_with_status(row) for row in rows]

def _day_bounds(day: datetime) -> Tuple[datetime, datetime]:
    day = BUENOS_AIRES.localize(day) if day.tzinfo is None else day.astimezone(BUENOS_AIRES)
    return (day.replace(hour=0, minute=0, second=0, microsecond=0),
            day.replace(hour=23, minute=59, second=59, microsecond=999999))

def get_today_reminders(chat_id: int) -> List[Dict]:
    """Today's reminders of a chat, with their status (not cancelled ones)."""
    return _reminders_between(chat_id, *_day_bounds(datetime.now(BUENOS_AIRES)), only_active=False)

def get_date_reminders(chat_id: int, target_date: datetime) -> List[Dict]:
    """The reminders of a day, past or future, with their status (not cancelled ones)."""
    return _reminders_between(chat_id, *_day_bounds(target_date), only_active=False)

def get_week_reminders(chat_id: int, include_sent: bool = False) -> List[Dict]:
    """This week's reminders (Monday to Sunday): pending ones, or all but cancelled ones."""
    from datetime import timedelta

    now = datetime.now(BUENOS_AIRES)
    monday, _ = _day_bounds(now - timedelta(days=now.weekday()))
    _, sunday_end = _day_bounds(monday + timedelta(days=6))
    return _reminders_between(chat_id, monday, sunday_end, only_active=not include_sent)

def search_reminders(chat_id: int, keyword: str) -> List[Dict]:
    """Search active reminders by keyword in text."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Use LIKE with wildcards for partial matching, case-insensitive
    search_pattern = f"%{keyword.lower()}%"

    cursor.execute('''
        SELECT id, text, datetime
        FROM reminders
        WHERE chat_id = ? AND status = 'active'
        AND LOWER(text) LIKE ?
        ORDER BY datetime
    ''', (chat_id, search_pattern))

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        reminders.append({
            'id': row[0],
            'text': row[1],
            'datetime': datetime.fromisoformat(row[2])
        })

    return reminders

FINISHED_STATUSES = ('sent', 'completed', 'cancelled', 'failed')

def get_historical_reminders(chat_id: int, status_filter: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """Finished reminders of a chat (sent, completed, cancelled, failed), newest first.

    status_filter keeps only one of those statuses.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if status_filter in FINISHED_STATUSES:
        cursor.execute('''
            SELECT id, text, datetime, status, is_important, repeat_interval
            FROM reminders
            WHERE chat_id = ? AND status = ?
            ORDER BY datetime DESC
            LIMIT ?
        ''', (chat_id, status_filter, limit))
    else:
        cursor.execute('''
            SELECT id, text, datetime, status, is_important, repeat_interval
            FROM reminders
            WHERE chat_id = ? AND status IN ('sent', 'completed', 'cancelled', 'failed')
            ORDER BY datetime DESC
            LIMIT ?
        ''', (chat_id, limit))

    rows = cursor.fetchall()
    conn.close()

    return [_reminder_with_status(row) for row in rows]

def search_reminder_history(chat_id: int, term: str, by_category: bool = False, limit: int = 10) -> List[Dict]:
    """Finished reminders whose text contains term (accent-insensitive) or with that category.

    Newest first, at most limit.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime, status, is_important, repeat_interval, category
        FROM reminders
        WHERE chat_id = ? AND status IN ('sent', 'completed', 'cancelled', 'failed')
        ORDER BY datetime DESC
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    normalized_term = normalize_text_for_search(term)
    matches = []
    for row in rows:
        if by_category:
            found = (row[6] or '').lower() == term.lower()
        else:
            found = normalized_term in normalize_text_for_search(row[1])
        if found:
            matches.append(_reminder_with_status(row))
            if len(matches) == limit:
                break
    return matches

def get_all_active_reminders() -> List[Dict]:
    """Active regular reminders from all chats. Important ones: get_active_important_reminders."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, text, datetime
        FROM reminders
        WHERE status = 'active' AND (is_important IS NULL OR is_important = FALSE)
    ''')

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        # Parse datetime and ensure it has timezone info
        dt = datetime.fromisoformat(row[3])
        if dt.tzinfo is None:
            # Assume Buenos Aires timezone for naive datetimes
            import pytz
            dt = pytz.timezone('America/Argentina/Buenos_Aires').localize(dt)

        reminders.append({
            'id': row[0],
            'chat_id': row[1],
            'text': row[2],
            'datetime': dt
        })

    return reminders

def cancel_reminder(chat_id: int, reminder_id: int) -> bool:
    """Cancel a specific reminder."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE reminders
        SET status = 'cancelled'
        WHERE id = ? AND chat_id = ? AND status = 'active'
    ''', (reminder_id, chat_id))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    if affected_rows > 0:
        logger.info(f"Reminder {reminder_id} cancelled")
        return True
    else:
        logger.warning(f"Could not cancel reminder {reminder_id}")
        return False

def cancel_multiple_reminders(chat_id: int, reminder_ids: List[int]) -> Dict[str, List[int]]:
    """Cancel multiple reminders and return results."""
    if not reminder_ids:
        return {"cancelled": [], "not_found": []}

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cancelled = []
    not_found = []

    for reminder_id in reminder_ids:
        cursor.execute('''
            UPDATE reminders
            SET status = 'cancelled'
            WHERE id = ? AND chat_id = ? AND status = 'active'
        ''', (reminder_id, chat_id))

        if cursor.rowcount > 0:
            cancelled.append(reminder_id)
            logger.info(f"Reminder {reminder_id} cancelled")
        else:
            not_found.append(reminder_id)
            logger.warning(f"Could not cancel reminder {reminder_id}")

    conn.commit()
    conn.close()

    return {"cancelled": cancelled, "not_found": not_found}

def cancel_all_reminders(chat_id: int) -> int:
    """Cancel all active reminders for a chat and return count."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE reminders
        SET status = 'cancelled'
        WHERE chat_id = ? AND status = 'active'
    ''', (chat_id,))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    logger.info(f"Cancelled {affected_rows} reminders for chat {chat_id}")
    return affected_rows

def _finish_active_reminder(reminder_id: int, status: str) -> bool:
    """Move an active reminder to a final status. False if it was no longer active."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE reminders
        SET status = ?
        WHERE id = ? AND status = 'active'
    ''', (status, reminder_id))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if success:
        logger.info(f"Reminder {reminder_id} marked as {status}")
    return success

def mark_reminder_sent(reminder_id: int) -> bool:
    """Mark an active reminder as sent."""
    return _finish_active_reminder(reminder_id, 'sent')

def mark_reminder_failed(reminder_id: int) -> bool:
    """Mark an active reminder that could not be delivered (shown in /historial)."""
    return _finish_active_reminder(reminder_id, 'failed')

# Vault functions
def add_vault_entry(chat_id: int, text: str, category: str = 'general') -> int:
    """Add a new entry to the vault."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    created_at = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO vault (chat_id, text, created_at, category)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, text, created_at, category))

    vault_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Vault entry {vault_id} added for chat {chat_id} with category '{category}'")
    return vault_id

def get_vault_entries(chat_id: int) -> List[Dict]:
    """Get all active vault entries for a chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, created_at, category
        FROM vault
        WHERE chat_id = ? AND (status IS NULL OR status = 'active')
        ORDER BY created_at DESC
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            'id': row[0],
            'text': row[1],
            'created_at': datetime.fromisoformat(row[2]),
            'category': row[3] if len(row) > 3 else 'general'
        })

    return entries

def search_vault_entries(chat_id: int, keyword: str) -> List[Dict]:
    """Search vault entries by keyword in text."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Use LIKE with wildcards for partial matching, case-insensitive
    search_pattern = f"%{keyword.lower()}%"

    cursor.execute('''
        SELECT id, text, created_at, category
        FROM vault
        WHERE chat_id = ? AND LOWER(text) LIKE ? AND (status IS NULL OR status = 'active')
        ORDER BY created_at DESC
    ''', (chat_id, search_pattern))

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            'id': row[0],
            'text': row[1],
            'created_at': datetime.fromisoformat(row[2]),
            'category': row[3] if len(row) > 3 else 'general'
        })

    return entries

def normalize_text_for_search(text: str) -> str:
    """Normalize text for search: remove accents, convert to lowercase."""
    if not text:
        return ""

    # Remove accents/diacritics
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # Convert to lowercase
    return without_accents.lower()

def search_reminders_fuzzy(chat_id: int, keyword: str) -> List[Dict]:
    """Search active reminders with fuzzy matching (accent-insensitive, partial matches)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Normalize the search keyword
    normalized_keyword = normalize_text_for_search(keyword)

    cursor.execute('''
        SELECT id, text, datetime, category
        FROM reminders
        WHERE chat_id = ? AND status = 'active'
        ORDER BY datetime
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    # Filter results using normalized text comparison
    filtered_reminders = []
    for row in rows:
        normalized_text = normalize_text_for_search(row[1])  # row[1] is text
        if normalized_keyword in normalized_text:
            filtered_reminders.append({
                'id': row[0],
                'text': row[1],
                'datetime': datetime.fromisoformat(row[2]),
                'category': row[3] if len(row) > 3 else 'general'
            })

    return filtered_reminders

def search_vault_fuzzy(chat_id: int, keyword: str) -> List[Dict]:
    """Search vault entries with fuzzy matching (accent-insensitive, partial matches)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Normalize the search keyword
    normalized_keyword = normalize_text_for_search(keyword)

    cursor.execute('''
        SELECT id, text, created_at, category
        FROM vault
        WHERE chat_id = ? AND (status IS NULL OR status = 'active')
        ORDER BY created_at DESC
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    # Filter results using normalized text comparison
    filtered_entries = []
    for row in rows:
        normalized_text = normalize_text_for_search(row[1])  # row[1] is text
        if normalized_keyword in normalized_text:
            filtered_entries.append({
                'id': row[0],
                'text': row[1],
                'created_at': datetime.fromisoformat(row[2]),
                'category': row[3] if len(row) > 3 else 'general'
            })

    return filtered_entries

def search_vault_conversational(chat_id: int, search_terms: List[str]) -> List[Dict]:
    """Search vault entries using multiple terms with scoring (for conversational queries)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, created_at, category
        FROM vault
        WHERE chat_id = ? AND (status IS NULL OR status = 'active')
        ORDER BY created_at DESC
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    # Score and filter results
    scored_entries = []
    for row in rows:
        normalized_text = normalize_text_for_search(row[1])
        score = 0

        # Count how many search terms appear in the text
        for term in search_terms:
            if term in normalized_text:
                score += 1

        # Only include entries that contain at least one term
        if score > 0:
            scored_entries.append({
                'id': row[0],
                'text': row[1],
                'created_at': datetime.fromisoformat(row[2]),
                'category': row[3] if len(row) > 3 else 'general',
                'score': score
            })

    # Sort by score (highest first), then by date (newest first)
    scored_entries.sort(key=lambda x: (-x['score'], -x['created_at'].timestamp()))

    return scored_entries

def search_reminders_by_category(chat_id: int, category: str) -> List[Dict]:
    """Search active reminders by category."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime, category
        FROM reminders
        WHERE chat_id = ? AND status = 'active' AND LOWER(category) = ?
        ORDER BY datetime
    ''', (chat_id, category.lower()))

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        reminders.append({
            'id': row[0],
            'text': row[1],
            'datetime': datetime.fromisoformat(row[2]),
            'category': row[3] if len(row) > 3 else 'general'
        })

    return reminders

def search_vault_by_category(chat_id: int, category: str) -> List[Dict]:
    """Search vault entries by category."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, created_at, category
        FROM vault
        WHERE chat_id = ? AND LOWER(category) = ? AND (status IS NULL OR status = 'active')
        ORDER BY created_at DESC
    ''', (chat_id, category.lower()))

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            'id': row[0],
            'text': row[1],
            'created_at': datetime.fromisoformat(row[2]),
            'category': row[3] if len(row) > 3 else 'general'
        })

    return entries

def delete_vault_entry(chat_id: int, vault_id: int) -> bool:
    """Mark a vault entry as deleted (soft delete)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE vault
        SET status = 'deleted', deleted_at = CURRENT_TIMESTAMP
        WHERE id = ? AND chat_id = ? AND status = 'active'
    ''', (vault_id, chat_id))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    if affected_rows > 0:
        logger.info(f"Vault entry {vault_id} marked as deleted")
        return True
    else:
        logger.warning(f"Could not delete vault entry {vault_id}")
        return False

# User management functions
def create_or_update_user(chat_id: int, username: str = None, first_name: str = None,
                         last_name: str = None, is_bot: bool = False, language_code: str = 'es') -> int:
    """Create or update user information."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    # Try to update existing user first
    cursor.execute('''
        UPDATE users
        SET username = ?, first_name = ?, last_name = ?, is_bot = ?,
            language_code = ?, last_activity = ?
        WHERE chat_id = ?
    ''', (username, first_name, last_name, int(is_bot), language_code, now, chat_id))

    if cursor.rowcount == 0:
        # User doesn't exist, create new one
        cursor.execute('''
            INSERT INTO users (chat_id, username, first_name, last_name, is_bot, language_code, created_at, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (chat_id, username, first_name, last_name, int(is_bot), language_code, now, now))
        user_id = cursor.lastrowid
        logger.info(f"Created new user {user_id} for chat {chat_id}")
    else:
        # Get existing user ID
        cursor.execute('SELECT id FROM users WHERE chat_id = ?', (chat_id,))
        user_id = cursor.fetchone()[0]
        logger.debug(f"Updated user {user_id} for chat {chat_id}")

    conn.commit()
    conn.close()
    return user_id

def get_user_by_chat_id(chat_id: int) -> Optional[Dict]:
    """Get user information by chat_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, username, first_name, last_name, is_bot, language_code, created_at, last_activity
        FROM users WHERE chat_id = ?
    ''', (chat_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'id': row[0],
            'chat_id': row[1],
            'username': row[2],
            'first_name': row[3],
            'last_name': row[4],
            'is_bot': bool(row[5]),
            'language_code': row[6],
            'created_at': datetime.fromisoformat(row[7]),
            'last_activity': datetime.fromisoformat(row[8])
        }
    return None

def update_user_activity(chat_id: int) -> bool:
    """Update user's last activity timestamp."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute('''
        UPDATE users SET last_activity = ? WHERE chat_id = ?
    ''', (now, chat_id))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    return affected_rows > 0

def get_all_users() -> List[Dict]:
    """Get all users for admin purposes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, username, first_name, last_name, is_bot, language_code, created_at, last_activity
        FROM users ORDER BY created_at DESC
    ''')

    rows = cursor.fetchall()
    conn.close()

    users = []
    for row in rows:
        users.append({
            'id': row[0],
            'chat_id': row[1],
            'username': row[2],
            'first_name': row[3],
            'last_name': row[4],
            'is_bot': bool(row[5]),
            'language_code': row[6],
            'created_at': datetime.fromisoformat(row[7]),
            'last_activity': datetime.fromisoformat(row[8])
        })

    return users

def get_user_info(chat_id: int) -> Dict:
    """Get user information by chat_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT chat_id, username, first_name, last_name, created_at, last_activity
        FROM users
        WHERE chat_id = ?
    ''', (chat_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'chat_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'created_at': datetime.fromisoformat(row[4]),
            'last_activity': datetime.fromisoformat(row[5])
        }
    return {}

def get_all_user_reminders(chat_id: int, include_history: bool = True) -> List[Dict]:
    """Get all reminders for a user, optionally including historical ones."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if include_history:
        status_filter = "status IN ('active', 'sent', 'cancelled')"
    else:
        status_filter = "status = 'active'"

    cursor.execute(f'''
        SELECT id, text, datetime, status, category, created_at
        FROM reminders
        WHERE chat_id = ? AND {status_filter}
        ORDER BY datetime DESC
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        # Parse datetime and ensure it has timezone info
        dt = datetime.fromisoformat(row[2])
        if dt.tzinfo is None:
            # Assume Buenos Aires timezone for naive datetimes
            import pytz
            dt = pytz.timezone('America/Argentina/Buenos_Aires').localize(dt)

        reminders.append({
            'id': row[0],
            'text': row[1],
            'datetime': dt,
            'status': row[3],
            'category': row[4] if row[4] else 'general',
            'created_at': datetime.fromisoformat(row[5])
        })

    return reminders

def get_all_user_vault_entries(chat_id: int, include_history: bool = True) -> List[Dict]:
    """Get all vault entries for a user, optionally including deleted ones."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if include_history:
        status_filter = "(status IS NULL OR status IN ('active', 'deleted'))"
    else:
        status_filter = "(status IS NULL OR status = 'active')"

    cursor.execute(f'''
        SELECT id, text, created_at, category, status, deleted_at
        FROM vault
        WHERE chat_id = ? AND {status_filter}
        ORDER BY created_at DESC
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entry = {
            'id': row[0],
            'text': row[1],
            'created_at': datetime.fromisoformat(row[2]),
            'category': row[3] if row[3] else 'general',
            'status': row[4] if row[4] else 'active'
        }

        if row[5]:  # deleted_at
            entry['deleted_at'] = datetime.fromisoformat(row[5])

        entries.append(entry)

    return entries

def delete_all_vault_entries(chat_id: int) -> int:
    """Mark all active vault entries as deleted (soft delete all)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE vault
        SET status = 'deleted', deleted_at = CURRENT_TIMESTAMP
        WHERE chat_id = ? AND status = 'active'
    ''', (chat_id,))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    logger.info(f"Marked {affected_rows} vault entries as deleted for chat {chat_id}")
    return affected_rows

def get_vault_history(chat_id: int) -> List[Dict]:
    """Get deleted vault entries (history)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, created_at, deleted_at, category
        FROM vault
        WHERE chat_id = ? AND status = 'deleted'
        ORDER BY deleted_at DESC
        LIMIT 20
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            'id': row[0],
            'text': row[1],
            'created_at': datetime.fromisoformat(row[2]),
            'deleted_at': datetime.fromisoformat(row[3]) if row[3] else None,
            'category': row[4] if len(row) > 4 else 'general'
        })

    return entries

# Export functions (aliases for backwards compatibility)
def get_all_reminders_for_export(chat_id: int) -> List[Dict]:
    """Get all reminders for export (includes all statuses)."""
    return get_all_user_reminders(chat_id, include_history=True)

def get_all_vault_entries_for_export(chat_id: int) -> List[Dict]:
    """Get all vault entries for export (includes deleted ones)."""
    return get_all_user_vault_entries(chat_id, include_history=True)

def add_important_reminder(chat_id: int, text: str, datetime_obj: datetime, category: str = None, repeat_interval: int = 5) -> int:
    """Add an important reminder with repeat interval."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO reminders (chat_id, text, datetime, category, is_important, repeat_interval, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, text, datetime_obj.isoformat(), category or 'general', True, repeat_interval, datetime.now().isoformat()))

    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Added important reminder {reminder_id} for chat {chat_id} with {repeat_interval}min interval")
    return reminder_id

def complete_reminder(chat_id: int, reminder_id: int) -> bool:
    """Mark an active reminder, regular or important, as completed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE reminders
        SET status = 'completed'
        WHERE id = ? AND chat_id = ? AND status = 'active'
    ''', (reminder_id, chat_id))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if success:
        logger.info(f"Completed reminder {reminder_id} for chat {chat_id}")

    return success

def record_important_reminder_sent(reminder_id: int) -> bool:
    """Record one more delivery of an important reminder: last_sent and times_sent."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE reminders
        SET last_sent = ?, times_sent = COALESCE(times_sent, 0) + 1
        WHERE id = ? AND is_important = TRUE AND status = 'active'
    ''', (datetime.now(BUENOS_AIRES).isoformat(), reminder_id))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return success

def _aware(value: Optional[str], naive_means_local: bool = False) -> Optional[datetime]:
    """Parse an ISO timestamp into an aware datetime.

    Naive reminder dates are Buenos Aires time. Old naive last_sent values were written
    with the server clock, so naive_means_local reads them as the server's local time.
    """
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        return parsed
    return parsed.astimezone() if naive_means_local else BUENOS_AIRES.localize(parsed)

def _reminder_for_scheduling(row) -> Dict:
    """Row with: id, chat_id, text, datetime, is_important, repeat_interval, last_sent, times_sent, category."""
    return {
        'id': row[0],
        'chat_id': row[1],
        'text': row[2],
        'datetime': _aware(row[3]),
        'is_important': bool(row[4]),
        'repeat_interval': row[5],
        'last_sent': _aware(row[6], naive_means_local=True),
        'times_sent': row[7] or 0,
        'category': row[8] or 'general'
    }

def get_active_reminder(reminder_id: int) -> Optional[Dict]:
    """An active reminder, regular or important, with what the scheduler needs; None if not active."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, text, datetime, is_important, repeat_interval, last_sent, times_sent, category
        FROM reminders
        WHERE id = ? AND status = 'active'
    ''', (reminder_id,))

    row = cursor.fetchone()
    conn.close()

    return _reminder_for_scheduling(row) if row else None

def get_active_important_reminders() -> List[Dict]:
    """Get all active important reminders for scheduler processing."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, text, datetime, is_important, repeat_interval, last_sent, times_sent, category
        FROM reminders
        WHERE is_important = TRUE AND status = 'active'
        ORDER BY datetime
    ''')

    rows = cursor.fetchall()
    conn.close()

    return [_reminder_for_scheduling(row) for row in rows]

# Special girlfriend mode functions
# A right answer to /novia leaves a request; an admin approves it (the mode is on) or
# rejects it (the chat cannot ask again until an admin approves it).
GIRLFRIEND_REQUEST_PENDING = 'pending'
GIRLFRIEND_REQUEST_REJECTED = 'rejected'

def _update_user_girlfriend_state(sql: str, params: tuple) -> bool:
    """Run an UPDATE on users; True if it changed a row."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql, params)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def request_girlfriend_mode(chat_id: int) -> bool:
    """Leave a pending request. False if the chat has the mode or already has a request."""
    success = _update_user_girlfriend_state('''
        UPDATE users
        SET girlfriend_request = ?, girlfriend_requested_at = ?
        WHERE chat_id = ? AND is_girlfriend = FALSE AND girlfriend_request IS NULL
    ''', (GIRLFRIEND_REQUEST_PENDING, datetime.now().isoformat(), chat_id))

    if success:
        logger.info(f"Girlfriend mode requested by chat {chat_id}")
    return success

def approve_girlfriend_request(chat_id: int) -> bool:
    """Turn the mode on for a chat with a pending or rejected request."""
    success = _update_user_girlfriend_state('''
        UPDATE users
        SET is_girlfriend = TRUE, girlfriend_activated_at = ?,
            girlfriend_request = NULL, girlfriend_requested_at = NULL
        WHERE chat_id = ? AND girlfriend_request IS NOT NULL
    ''', (datetime.now().isoformat(), chat_id))

    if success:
        logger.info(f"Girlfriend mode approved for chat {chat_id}")
    return success

def reject_girlfriend_request(chat_id: int) -> bool:
    """Reject a pending request: the chat cannot ask again."""
    success = _update_user_girlfriend_state('''
        UPDATE users
        SET girlfriend_request = ?
        WHERE chat_id = ? AND girlfriend_request = ?
    ''', (GIRLFRIEND_REQUEST_REJECTED, chat_id, GIRLFRIEND_REQUEST_PENDING))

    if success:
        logger.info(f"Girlfriend mode request rejected for chat {chat_id}")
    return success

def get_girlfriend_request(chat_id: int) -> Optional[str]:
    """GIRLFRIEND_REQUEST_PENDING, GIRLFRIEND_REQUEST_REJECTED or None."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT girlfriend_request FROM users WHERE chat_id = ?', (chat_id,))

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def get_pending_girlfriend_requests() -> List[Dict]:
    """Chats waiting for an admin to approve the mode, oldest request first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT chat_id, first_name, username, girlfriend_requested_at
        FROM users
        WHERE girlfriend_request = ?
        ORDER BY girlfriend_requested_at
    ''', (GIRLFRIEND_REQUEST_PENDING,))

    rows = cursor.fetchall()
    conn.close()

    return [
        {'chat_id': row[0], 'first_name': row[1], 'username': row[2], 'requested_at': row[3]}
        for row in rows
    ]

def is_girlfriend(chat_id: int) -> bool:
    """Check if chat_id has girlfriend mode activated."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT is_girlfriend
        FROM users
        WHERE chat_id = ? AND is_girlfriend = TRUE
    ''', (chat_id,))

    result = cursor.fetchone()
    conn.close()

    return result is not None

def remove_girlfriend_mode(chat_id: int) -> bool:
    """Turn the mode off for a chat, which cannot ask again until an admin approves it.

    False if the chat did not have the mode.
    """
    success = _update_user_girlfriend_state('''
        UPDATE users
        SET is_girlfriend = FALSE, girlfriend_activated_at = NULL, girlfriend_request = ?
        WHERE chat_id = ? AND is_girlfriend = TRUE
    ''', (GIRLFRIEND_REQUEST_REJECTED, chat_id))

    if success:
        logger.info(f"Girlfriend mode removed for chat {chat_id}")
    return success

def get_girlfriend_chats() -> List[Dict]:
    """Chats with girlfriend mode activated, oldest activation first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT chat_id, first_name, username, girlfriend_activated_at
        FROM users
        WHERE is_girlfriend = TRUE
        ORDER BY girlfriend_activated_at
    ''')

    rows = cursor.fetchall()
    conn.close()

    return [
        {'chat_id': row[0], 'first_name': row[1], 'username': row[2], 'activated_at': row[3]}
        for row in rows
    ]

# Secret gallery functions
def add_secret_photo(local_file_path: str, file_type: str, uploaded_by: int, original_filename: str = None, description: str = None) -> int:
    """Add a photo/meme to the secret gallery using local file storage."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO secret_gallery (local_file_path, file_type, original_filename, description, uploaded_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (local_file_path, file_type, original_filename, description, uploaded_by))

    photo_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Added secret photo {photo_id} to gallery by admin {uploaded_by}: {local_file_path}")
    return photo_id

def get_random_secret_photo() -> dict:
    """Get a random active photo from the secret gallery."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, local_file_path, file_type, original_filename, description
        FROM secret_gallery
        WHERE is_active = TRUE AND local_file_path IS NOT NULL
        ORDER BY RANDOM()
        LIMIT 1
    ''')

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'id': row[0],
            'local_file_path': row[1],
            'file_type': row[2],
            'original_filename': row[3],
            'description': row[4]
        }
    return None

def get_secret_gallery_count() -> int:
    """Get the total number of active photos in the secret gallery."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) FROM secret_gallery WHERE is_active = TRUE AND local_file_path IS NOT NULL
    ''')

    count = cursor.fetchone()[0]
    conn.close()
    return count

def delete_secret_photo(photo_id: int, admin_chat_id: int) -> bool:
    """Soft delete a photo from the secret gallery (admin only)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE secret_gallery
        SET is_active = FALSE
        WHERE id = ? AND uploaded_by = ?
    ''', (photo_id, admin_chat_id))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if success:
        logger.info(f"Admin {admin_chat_id} deleted secret photo {photo_id}")

    return success

def mark_photo_invalid(photo_id: int) -> bool:
    """Mark a photo as invalid (e.g., when file_id fails to send)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE secret_gallery
        SET is_active = FALSE
        WHERE id = ?
    ''', (photo_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if success:
        logger.info(f"Marked secret photo {photo_id} as invalid")

    return success

def get_reminder_by_id(chat_id: int, reminder_id: int) -> dict:
    """Get a specific reminder by ID and chat_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime, created_at, category, is_important,
               repeat_interval, last_sent
        FROM reminders
        WHERE id = ? AND chat_id = ?
    ''', (reminder_id, chat_id))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'id': row[0],
            'text': row[1],
            'datetime': row[2],
            'created_at': row[3],
            'category': row[4],
            'is_important': bool(row[5]) if row[5] is not None else False,
            'repeat_interval': row[6],
            'last_sent': row[7]
        }

    return None

def get_all_active_reminders_for_date(target_date: datetime) -> Dict[int, List[Dict]]:
    """Get active reminders for a specific date across all chats, grouped by chat_id."""
    import pytz

    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    if target_date.tzinfo is None:
        target_date = timezone.localize(target_date)
    else:
        target_date = target_date.astimezone(timezone)

    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, text, datetime, is_important
        FROM reminders
        WHERE status = 'active'
        AND datetime >= ? AND datetime <= ?
        ORDER BY chat_id, datetime
    ''', (day_start.isoformat(), day_end.isoformat()))

    rows = cursor.fetchall()
    conn.close()

    reminders_by_chat: Dict[int, List[Dict]] = {}
    for row in rows:
        dt = datetime.fromisoformat(row[3])
        if dt.tzinfo is None:
            dt = timezone.localize(dt)

        reminders_by_chat.setdefault(row[1], []).append({
            'id': row[0],
            'text': row[2],
            'datetime': dt,
            'is_important': bool(row[4]) if row[4] is not None else False
        })

    return reminders_by_chat

# Bot-wide state
def get_app_state(key: str) -> Optional[str]:
    """Value stored under `key` in app_state, or None if it was never set."""
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute('SELECT value FROM app_state WHERE key = ?', (key,)).fetchone()
    finally:
        conn.close()

    return row[0] if row else None

def set_app_state(key: str, value: str):
    """Store `value` under `key` in app_state, replacing any previous value."""
    import pytz

    updated_at = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).isoformat()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute('''
            INSERT INTO app_state (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        ''', (key, value, updated_at))
        conn.commit()
    finally:
        conn.close()

def get_engaged_chat_ids() -> List[int]:
    """Chats that use the bot: at least one reminder or bitácora entry, in any status."""
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute('''
            SELECT chat_id FROM reminders
            UNION
            SELECT chat_id FROM vault
            ORDER BY chat_id
        ''').fetchall()
    finally:
        conn.close()

    return [row[0] for row in rows]
