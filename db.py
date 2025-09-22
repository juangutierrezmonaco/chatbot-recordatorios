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