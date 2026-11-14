"""Access to the admin and special modes (issue #14).

Run from the project root:
    python3 -m unittest discover -s tests -v
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import access  # noqa: E402
import db  # noqa: E402
from migrations import MigrationManager  # noqa: E402


def user(user_id):
    return SimpleNamespace(id=user_id)


class Admins(unittest.TestCase):
    def admins(self, value):
        with mock.patch.dict(os.environ, {access.ADMIN_USER_IDS_VARIABLE: value}):
            return access.admin_user_ids()

    def test_ids_separated_by_commas(self):
        self.assertEqual(self.admins('111, 222,333'), {111, 222, 333})

    def test_invalid_and_empty_entries_are_ignored(self):
        with self.assertLogs('access', 'ERROR'):
            self.assertEqual(self.admins('111,,abc, '), {111})

    def test_only_listed_users_are_admins(self):
        with mock.patch.dict(os.environ, {access.ADMIN_USER_IDS_VARIABLE: '111'}):
            self.assertTrue(access.is_admin(user(111)))
            self.assertFalse(access.is_admin(user(222)))
            self.assertFalse(access.is_admin(None))

    def test_nobody_is_admin_without_the_variable(self):
        with mock.patch.dict(os.environ, clear=True):
            self.assertEqual(access.admin_user_ids(), set())
            self.assertFalse(access.is_admin(user(111)))


class GirlfriendAnswer(unittest.TestCase):
    PHRASE = 'Brilla la luna, sobre el río'

    def is_answer(self, text, phrase=PHRASE):
        with mock.patch.dict(os.environ, {access.GIRLFRIEND_PHRASE_VARIABLE: phrase}):
            return access.is_girlfriend_answer(text)

    def test_exact_phrase(self):
        self.assertTrue(self.is_answer('Brilla la luna, sobre el río'))

    def test_case_accents_punctuation_and_order_do_not_matter(self):
        self.assertTrue(self.is_answer('sobre el RIO brilla la luna!!'))

    def test_a_few_extra_words_are_allowed(self):
        self.assertTrue(self.is_answer('jaja brilla la luna sobre el río te amo'))

    def test_a_missing_word_is_not_enough(self):
        self.assertFalse(self.is_answer('brilla la luna sobre el mar'))

    def test_a_word_inside_another_does_not_count(self):
        self.assertFalse(self.is_answer('brillante la lunar sobre el río'))

    def test_a_long_list_of_words_does_not_pass(self):
        self.assertFalse(self.is_answer('brilla la luna sobre el río y el sol y el mar y las estrellas'))

    def test_no_phrase_configured_means_no_answer_is_right(self):
        with mock.patch.dict(os.environ, clear=True):
            self.assertFalse(access.girlfriend_mode_available())
            self.assertFalse(access.is_girlfriend_answer(''))
            self.assertFalse(access.is_girlfriend_answer('cualquier cosa'))
        self.assertFalse(self.is_answer('', phrase=' ¡! '))

    def test_empty_message(self):
        self.assertFalse(self.is_answer(None))


class FailedAttempts(unittest.TestCase):
    USER = 42

    def setUp(self):
        access.clear_failed_attempts(self.USER)

    def tearDown(self):
        access.clear_failed_attempts(self.USER)

    def fail_times(self, times, now):
        for _ in range(times):
            access.record_failed_attempt(self.USER, now)

    def test_locked_after_too_many_wrong_answers(self):
        self.fail_times(access.MAX_FAILED_ATTEMPTS - 1, now=1000)
        self.assertFalse(access.is_locked_out(self.USER, now=1000))
        self.fail_times(1, now=1000)
        self.assertTrue(access.is_locked_out(self.USER, now=1000))

    def test_unlocked_once_the_window_passes(self):
        self.fail_times(access.MAX_FAILED_ATTEMPTS, now=1000)
        later = 1000 + access.FAILED_ATTEMPTS_WINDOW_SECONDS
        self.assertFalse(access.is_locked_out(self.USER, now=later))

    def test_a_right_answer_clears_the_count(self):
        self.fail_times(access.MAX_FAILED_ATTEMPTS, now=1000)
        access.clear_failed_attempts(self.USER)
        self.assertFalse(access.is_locked_out(self.USER, now=1000))

    def test_counted_per_user(self):
        self.fail_times(access.MAX_FAILED_ATTEMPTS, now=1000)
        self.assertFalse(access.is_locked_out(self.USER + 1, now=1000))


class GirlfriendChats(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tmp_dir.name, 'test.db')

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tmp_dir.cleanup()

    def migrate(self, up_to=None):
        manager = MigrationManager(db.DB_PATH, migrations_dir=os.path.join(ROOT, 'migrations'))
        if up_to is None:
            manager.run_migrations()
            return

        with tempfile.TemporaryDirectory() as partial_dir:
            for number in range(1, up_to + 1):
                with open(os.path.join(ROOT, 'migrations', f'{number}.sql'), encoding='utf-8') as source, \
                        open(os.path.join(partial_dir, f'{number}.sql'), 'w', encoding='utf-8') as copy:
                    copy.write(source.read())
            MigrationManager(db.DB_PATH, migrations_dir=partial_dir).run_migrations()

    def test_list_and_remove(self):
        self.migrate()
        db.create_or_update_user(1, first_name='Ana')
        db.create_or_update_user(2, username='otro')
        db.create_or_update_user(3, first_name='Sin modo')
        db.set_girlfriend_mode(1)
        db.set_girlfriend_mode(2)

        chats = db.get_girlfriend_chats()
        self.assertEqual([chat['chat_id'] for chat in chats], [1, 2])
        self.assertEqual(chats[0]['first_name'], 'Ana')
        self.assertEqual(chats[1]['username'], 'otro')

        self.assertTrue(db.remove_girlfriend_mode(1))
        self.assertFalse(db.is_girlfriend(1))
        self.assertFalse(db.remove_girlfriend_mode(1))
        self.assertFalse(db.remove_girlfriend_mode(3))
        self.assertEqual([chat['chat_id'] for chat in db.get_girlfriend_chats()], [2])

    def test_migration_12_clears_the_modes_activated_with_the_old_values(self):
        self.migrate(up_to=11)
        db.create_or_update_user(1, first_name='Dueño')
        db.set_girlfriend_mode(1)
        with sqlite3.connect(db.DB_PATH) as conn:
            conn.execute("UPDATE users SET is_admin = TRUE, admin_activated_at = '2025-09-23' WHERE chat_id = 1")

        self.migrate()

        self.assertFalse(db.is_girlfriend(1))
        with sqlite3.connect(db.DB_PATH) as conn:
            row = conn.execute(
                "SELECT is_admin, admin_activated_at, girlfriend_activated_at FROM users WHERE chat_id = 1"
            ).fetchone()
        self.assertEqual(row, (0, None, None))


if __name__ == '__main__':
    unittest.main()
