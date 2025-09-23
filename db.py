import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional
import unicodedata
from migrations import MigrationManager

logger = logging.getLogger(__name__)

DB_PATH = "reminders.db"

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
        SELECT id, text, datetime, category
        FROM reminders
        WHERE chat_id = ? AND status = 'active'
        ORDER BY datetime
    ''', (chat_id,))

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

def get_today_reminders(chat_id: int) -> List[Dict]:
    """Get all active and sent reminders for today for a chat."""
    import pytz

    # Get today's date range in Buenos Aires timezone
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    now = datetime.now(timezone)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime, status
        FROM reminders
        WHERE chat_id = ? AND status IN ('active', 'sent')
        AND datetime >= ? AND datetime <= ?
        ORDER BY datetime
    ''', (chat_id, today_start.isoformat(), today_end.isoformat()))

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        reminders.append({
            'id': row[0],
            'text': row[1],
            'datetime': datetime.fromisoformat(row[2]),
            'status': row[3]
        })

    return reminders

def get_week_reminders(chat_id: int, include_sent: bool = False) -> List[Dict]:
    """Get reminders for the current week for a chat.

    Args:
        chat_id: The chat ID
        include_sent: If True, include sent reminders. If False, only active reminders.
    """
    import pytz
    from datetime import timedelta

    # Get this week's date range in Buenos Aires timezone
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    now = datetime.now(timezone)

    # Get start of week (Monday)
    days_since_monday = now.weekday()
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)

    # Get end of week (Sunday)
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Choose status filter based on include_sent parameter
    if include_sent:
        status_filter = "status IN ('active', 'sent')"
    else:
        status_filter = "status = 'active'"

    cursor.execute(f'''
        SELECT id, text, datetime, status
        FROM reminders
        WHERE chat_id = ? AND {status_filter}
        AND datetime >= ? AND datetime <= ?
        ORDER BY datetime
    ''', (chat_id, week_start.isoformat(), week_end.isoformat()))

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        reminders.append({
            'id': row[0],
            'text': row[1],
            'datetime': datetime.fromisoformat(row[2]),
            'status': row[3]
        })

    return reminders

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

def get_date_reminders(chat_id: int, target_date: datetime) -> List[Dict]:
    """Get all active reminders for a specific date."""
    import pytz

    # Ensure target_date has timezone info
    if target_date.tzinfo is None:
        timezone = pytz.timezone('America/Argentina/Buenos_Aires')
        target_date = timezone.localize(target_date)

    # Get date range for the target day
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime
        FROM reminders
        WHERE chat_id = ? AND status = 'active'
        AND datetime >= ? AND datetime <= ?
        ORDER BY datetime
    ''', (chat_id, day_start.isoformat(), day_end.isoformat()))

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

def get_historical_reminders(chat_id: int, status_filter: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """Get historical reminders (sent/cancelled) for a chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if status_filter and status_filter in ['sent', 'cancelled']:
        cursor.execute('''
            SELECT id, text, datetime, status
            FROM reminders
            WHERE chat_id = ? AND status = ?
            ORDER BY datetime DESC
            LIMIT ?
        ''', (chat_id, status_filter, limit))
    else:
        # Get both sent and cancelled
        cursor.execute('''
            SELECT id, text, datetime, status
            FROM reminders
            WHERE chat_id = ? AND status IN ('sent', 'cancelled')
            ORDER BY datetime DESC
            LIMIT ?
        ''', (chat_id, limit))

    rows = cursor.fetchall()
    conn.close()

    reminders = []
    for row in rows:
        reminders.append({
            'id': row[0],
            'text': row[1],
            'datetime': datetime.fromisoformat(row[2]),
            'status': row[3]
        })

    return reminders

def get_all_active_reminders() -> List[Dict]:
    """Get all active reminders from all chats."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, text, datetime
        FROM reminders
        WHERE status = 'active'
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

def mark_reminder_sent(reminder_id: int):
    """Mark a reminder as sent."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE reminders
        SET status = 'sent'
        WHERE id = ?
    ''', (reminder_id,))

    conn.commit()
    conn.close()
    logger.info(f"Reminder {reminder_id} marked as sent")

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