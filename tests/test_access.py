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

    def test_the_mode_needs_the_phrase_and_an_admin_to_approve(self):
        phrase = {access.GIRLFRIEND_PHRASE_VARIABLE: self.PHRASE}
        admins = {access.ADMIN_USER_IDS_VARIABLE: '111'}
        with mock.patch.dict(os.environ, {**phrase, **admins}, clear=True):
            self.assertTrue(access.girlfriend_mode_available())
        with mock.patch.dict(os.environ, phrase, clear=True):
            self.assertFalse(access.girlfriend_mode_available())
        with mock.patch.dict(os.environ, admins, clear=True):
            self.assertFalse(access.girlfriend_mode_available())

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


class GirlfriendRequests(unittest.TestCase):
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

    def chat_ids(self, chats):
        return [chat['chat_id'] for chat in chats]

    def test_a_request_waits_for_an_admin(self):
        self.migrate()
        db.create_or_update_user(1, first_name='Ana')

        self.assertIsNone(db.get_girlfriend_request(1))
        self.assertTrue(db.request_girlfriend_mode(1))
        self.assertEqual(db.get_girlfriend_request(1), db.GIRLFRIEND_REQUEST_PENDING)
        self.assertFalse(db.is_girlfriend(1))
        self.assertFalse(db.request_girlfriend_mode(1), 'already pending')

        pending = db.get_pending_girlfriend_requests()
        self.assertEqual(self.chat_ids(pending), [1])
        self.assertEqual(pending[0]['first_name'], 'Ana')

    def test_approving_turns_the_mode_on(self):
        self.migrate()
        db.create_or_update_user(1, first_name='Ana')
        db.request_girlfriend_mode(1)

        self.assertTrue(db.approve_girlfriend_request(1))
        self.assertTrue(db.is_girlfriend(1))
        self.assertIsNone(db.get_girlfriend_request(1))
        self.assertEqual(db.get_pending_girlfriend_requests(), [])
        self.assertEqual(self.chat_ids(db.get_girlfriend_chats()), [1])
        self.assertFalse(db.request_girlfriend_mode(1), 'already has the mode')

    def test_a_chat_without_a_request_cannot_be_approved(self):
        self.migrate()
        db.create_or_update_user(1, first_name='Ana')
        self.assertFalse(db.approve_girlfriend_request(1))
        self.assertFalse(db.approve_girlfriend_request(999))
        self.assertFalse(db.is_girlfriend(1))

    def test_a_rejected_chat_cannot_ask_again_until_approved(self):
        self.migrate()
        db.create_or_update_user(1, first_name='Ana')
        db.request_girlfriend_mode(1)

        self.assertTrue(db.reject_girlfriend_request(1))
        self.assertEqual(db.get_girlfriend_request(1), db.GIRLFRIEND_REQUEST_REJECTED)
        self.assertFalse(db.reject_girlfriend_request(1), 'no longer pending')
        self.assertFalse(db.request_girlfriend_mode(1))
        self.assertEqual(db.get_pending_girlfriend_requests(), [])

        self.assertTrue(db.approve_girlfriend_request(1), 'an admin can change their mind')
        self.assertTrue(db.is_girlfriend(1))

    def test_removing_the_mode_blocks_new_requests(self):
        self.migrate()
        db.create_or_update_user(1, first_name='Ana')
        db.create_or_update_user(2, username='otro')
        for chat_id in (1, 2):
            db.request_girlfriend_mode(chat_id)
            db.approve_girlfriend_request(chat_id)
        self.assertEqual(self.chat_ids(db.get_girlfriend_chats()), [1, 2])
        self.assertEqual(db.get_girlfriend_chats()[1]['username'], 'otro')

        self.assertTrue(db.remove_girlfriend_mode(1))
        self.assertFalse(db.is_girlfriend(1))
        self.assertFalse(db.remove_girlfriend_mode(1))
        self.assertEqual(self.chat_ids(db.get_girlfriend_chats()), [2])
        self.assertFalse(db.request_girlfriend_mode(1))
        self.assertEqual(db.get_girlfriend_request(1), db.GIRLFRIEND_REQUEST_REJECTED)

    def test_migration_12_clears_the_modes_activated_with_the_old_values(self):
        self.migrate(up_to=11)
        db.create_or_update_user(1, first_name='Dueño')
        with sqlite3.connect(db.DB_PATH) as conn:
            conn.execute(
                "UPDATE users SET is_admin = TRUE, admin_activated_at = '2025-09-23', "
                "is_girlfriend = TRUE, girlfriend_activated_at = '2025-09-23' WHERE chat_id = 1"
            )

        self.migrate()

        self.assertFalse(db.is_girlfriend(1))
        self.assertIsNone(db.get_girlfriend_request(1))
        with sqlite3.connect(db.DB_PATH) as conn:
            row = conn.execute(
                "SELECT is_admin, admin_activated_at, girlfriend_activated_at FROM users WHERE chat_id = 1"
            ).fetchone()
        self.assertEqual(row, (0, None, None))


if __name__ == '__main__':
    unittest.main()
