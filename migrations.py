import os
import sqlite3
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class MigrationManager:
    """Manage database migrations with version control."""

    def __init__(self, db_path: str, migrations_dir: str = "migrations"):
        self.db_path = db_path
        self.migrations_dir = migrations_dir
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                sql_content TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Migrations table ensured")

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT version FROM schema_migrations ORDER BY version')
        versions = [row[0] for row in cursor.fetchall()]

        conn.close()
        return versions

    def get_pending_migrations(self) -> List[Dict]:
        """Get list of pending migration files."""
        if not os.path.exists(self.migrations_dir):
            return []

        applied = set(self.get_applied_migrations())
        migration_files = []

        # Sort files by numeric value (1.sql, 2.sql, etc.)
        sql_files = [f for f in os.listdir(self.migrations_dir) if f.endswith('.sql')]
        sql_files.sort(key=lambda x: int(x.replace('.sql', '')))

        for filename in sql_files:
            version = filename.replace('.sql', '')
            if version not in applied:
                file_path = os.path.join(self.migrations_dir, filename)
                migration_files.append({
                    'version': version,
                    'filename': filename,
                    'path': file_path
                })

        return migration_files

    def apply_migration(self, migration: Dict) -> bool:
        """Apply a single migration."""
        try:
            # Read migration SQL
            with open(migration['path'], 'r', encoding='utf-8') as f:
                sql_content = f.read()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Execute migration SQL
            cursor.executescript(sql_content)

            # Record migration as applied
            cursor.execute('''
                INSERT INTO schema_migrations (version, name, applied_at, sql_content)
                VALUES (?, ?, ?, ?)
            ''', (
                migration['version'],
                migration['filename'],
                datetime.now().isoformat(),
                sql_content
            ))

            conn.commit()
            conn.close()

            logger.info(f"Applied migration: {migration['version']}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply migration {migration['version']}: {e}")
            return False

    def run_migrations(self) -> bool:
        """Run all pending migrations."""
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return True

        logger.info(f"Found {len(pending)} pending migrations")

        for migration in pending:
            if not self.apply_migration(migration):
                logger.error(f"Migration failed, stopping at: {migration['version']}")
                return False

        logger.info("All migrations applied successfully")
        return True

    def create_migration(self, name: str, sql_content: str) -> str:
        """Create a new migration file with incremental numbering."""
        if not os.path.exists(self.migrations_dir):
            os.makedirs(self.migrations_dir)

        # Find the next migration number
        existing_files = [f for f in os.listdir(self.migrations_dir) if f.endswith('.sql')]
        if existing_files:
            numbers = [int(f.replace('.sql', '')) for f in existing_files]
            next_number = max(numbers) + 1
        else:
            next_number = 1

        filename = f"{next_number}.sql"
        file_path = os.path.join(self.migrations_dir, filename)

        # Add header comment to migration
        header = f"""-- Migration {next_number}: {name}
-- Created: {datetime.now().isoformat()}

"""

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(header + sql_content)

        logger.info(f"Created migration: {filename}")
        return file_path

    def get_migration_history(self) -> List[Dict]:
        """Get complete migration history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT version, name, applied_at, sql_content
            FROM schema_migrations
            ORDER BY applied_at DESC
        ''')

        history = []
        for row in cursor.fetchall():
            history.append({
                'version': row[0],
                'name': row[1],
                'applied_at': row[2],
                'sql_content': row[3]
            })

        conn.close()
        return history