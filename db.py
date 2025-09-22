import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = "reminders.db"

def init_db():
    """Initialize the database and create necessary tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            datetime TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized")

def add_reminder(chat_id: int, text: str, datetime_obj: datetime) -> int:
    """Add a new reminder to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO reminders (chat_id, text, datetime, status)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, text, datetime_obj.isoformat(), 'active'))

    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Reminder {reminder_id} added for chat {chat_id}")
    return reminder_id

def get_active_reminders(chat_id: int) -> List[Dict]:
    """Get all active reminders for a chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime
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
            'datetime': datetime.fromisoformat(row[2])
        })

    return reminders

def get_today_reminders(chat_id: int) -> List[Dict]:
    """Get all active reminders for today for a chat."""
    import pytz

    # Get today's date range in Buenos Aires timezone
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    now = datetime.now(timezone)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, datetime
        FROM reminders
        WHERE chat_id = ? AND status = 'active'
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
            'datetime': datetime.fromisoformat(row[2])
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
        reminders.append({
            'id': row[0],
            'chat_id': row[1],
            'text': row[2],
            'datetime': datetime.fromisoformat(row[3])
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
def add_vault_entry(chat_id: int, text: str) -> int:
    """Add a new entry to the vault."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    created_at = datetime.now().isoformat()

    cursor.execute('''
        INSERT INTO vault (chat_id, text, created_at)
        VALUES (?, ?, ?)
    ''', (chat_id, text, created_at))

    vault_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Vault entry {vault_id} added for chat {chat_id}")
    return vault_id

def get_vault_entries(chat_id: int) -> List[Dict]:
    """Get all vault entries for a chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, text, created_at
        FROM vault
        WHERE chat_id = ?
        ORDER BY created_at DESC
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            'id': row[0],
            'text': row[1],
            'created_at': datetime.fromisoformat(row[2])
        })

    return entries

def search_vault_entries(chat_id: int, keyword: str) -> List[Dict]:
    """Search vault entries by keyword in text."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Use LIKE with wildcards for partial matching, case-insensitive
    search_pattern = f"%{keyword.lower()}%"

    cursor.execute('''
        SELECT id, text, created_at
        FROM vault
        WHERE chat_id = ? AND LOWER(text) LIKE ?
        ORDER BY created_at DESC
    ''', (chat_id, search_pattern))

    rows = cursor.fetchall()
    conn.close()

    entries = []
    for row in rows:
        entries.append({
            'id': row[0],
            'text': row[1],
            'created_at': datetime.fromisoformat(row[2])
        })

    return entries

def delete_vault_entry(chat_id: int, vault_id: int) -> bool:
    """Delete a vault entry."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM vault
        WHERE id = ? AND chat_id = ?
    ''', (vault_id, chat_id))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    if affected_rows > 0:
        logger.info(f"Vault entry {vault_id} deleted")
        return True
    else:
        logger.warning(f"Could not delete vault entry {vault_id}")
        return False