"""Release announcements sent after a deploy.

Run from the project root:
    python3 -m unittest discover -s tests -v
"""
import asyncio
import os
import sys
import tempfile
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import announcements  # noqa: E402
import db  # noqa: E402
from migrations import MigrationManager  # noqa: E402


def release(version, *notes):
    return {'version': version, 'notes': list(notes)}


RELEASES = [  # newest first, as in release_notes.json
    release('2026-11-20', 'Tercera'),
    release('2026-11-15', 'Segunda'),
    release('2026-11-13', 'Primera'),
]


class PendingReleases(unittest.TestCase):
    def versions(self, last_announced):
        return [r['version'] for r in announcements.pending_releases(RELEASES, last_announced)]

    def test_nothing_announced_yet_sends_only_the_newest(self):
        self.assertEqual(self.versions(None), ['2026-11-20'])

    def test_newest_already_announced_sends_nothing(self):
        self.assertEqual(self.versions('2026-11-20'), [])

    def test_several_new_releases_are_sent_oldest_first(self):
        self.assertEqual(self.versions('2026-11-13'), ['2026-11-15', '2026-11-20'])

    def test_unknown_last_version_sends_only_the_newest(self):
        self.assertEqual(self.versions('2025-01-01'), ['2026-11-20'])

    def test_no_releases(self):
        self.assertEqual(announcements.pending_releases([], None), [])


class FormatMessages(unittest.TestCase):
    def test_header_bullets_and_escaping(self):
        messages = announcements.format_release_messages([
            release('v1', 'Usá `/manana` para ver mañana', 'Texto con <, > & sin romper'),
        ])
        self.assertEqual(messages, [
            '🆕 <b>Novedades del bot</b>\n\n'
            '• Usá <code>/manana</code> para ver mañana\n'
            '• Texto con &lt;, &gt; &amp; sin romper'
        ])

    def test_several_releases_are_listed_in_order(self):
        messages = announcements.format_release_messages([release('v1', 'Uno'), release('v2', 'Dos')])
        self.assertTrue(messages[0].endswith('• Uno\n• Dos'))

    def test_long_notes_are_split_under_the_telegram_limit(self):
        notes = [f'Nota {i} ' + 'x' * 300 for i in range(40)]
        messages = announcements.format_release_messages([release('v1', *notes)])
        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(message) <= 4096 for message in messages))
        self.assertEqual(sum(message.count('• ') for message in messages), 40)


class FakeBot:
    def __init__(self, unreachable=()):
        self.sent = []
        self.unreachable = set(unreachable)

    async def send_message(self, chat_id, text, parse_mode=None):
        if chat_id in self.unreachable:
            raise RuntimeError('Forbidden: bot was blocked by the user')
        self.sent.append((chat_id, text, parse_mode))


class AnnounceNewReleases(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tmp_dir.name, 'test.db')
        MigrationManager(db.DB_PATH, migrations_dir=os.path.join(ROOT, 'migrations')).run_migrations()
        self.original_pause = announcements.SECONDS_BETWEEN_CHATS
        announcements.SECONDS_BETWEEN_CHATS = 0

        # Chat 1 has reminders, chat 2 only bitácora notes, chat 3 only opened the bot
        db.add_reminder(1, 'Dentista', datetime(2026, 12, 1, 9, 0))
        db.add_vault_entry(2, 'Le gusta el vino tinto')
        db.create_or_update_user(3, first_name='Visitante')

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        announcements.SECONDS_BETWEEN_CHATS = self.original_pause
        self.tmp_dir.cleanup()

    def announce(self, bot, releases=RELEASES):
        return asyncio.run(announcements.announce_new_releases(bot, releases))

    def test_sent_to_chats_that_use_the_bot(self):
        bot = FakeBot()
        self.assertEqual(self.announce(bot), 2)
        self.assertEqual([chat_id for chat_id, _, _ in bot.sent], [1, 2])
        self.assertTrue(all(parse_mode == 'HTML' for _, _, parse_mode in bot.sent))
        self.assertIn('Tercera', bot.sent[0][1])

    def test_a_restart_does_not_send_it_again(self):
        self.announce(FakeBot())
        bot = FakeBot()
        self.assertEqual(self.announce(bot), 0)
        self.assertEqual(bot.sent, [])

    def test_a_new_release_is_sent_on_the_next_start(self):
        self.announce(FakeBot(), RELEASES[1:])
        bot = FakeBot()
        self.announce(bot)
        self.assertIn('Tercera', bot.sent[0][1])
        self.assertNotIn('Segunda', bot.sent[0][1])

    def test_an_unreachable_chat_does_not_stop_the_rest(self):
        bot = FakeBot(unreachable={1})
        self.assertEqual(self.announce(bot), 1)
        self.assertEqual([chat_id for chat_id, _, _ in bot.sent], [2])
        self.assertEqual(db.get_app_state(announcements.LAST_ANNOUNCED_KEY), '2026-11-20')

    def test_telegram_down_at_startup_retries_on_the_next_start(self):
        bot = FakeBot(unreachable={1, 2})
        self.assertEqual(self.announce(bot), 0)
        self.assertIsNone(db.get_app_state(announcements.LAST_ANNOUNCED_KEY))

        bot = FakeBot()
        self.assertEqual(self.announce(bot), 2)
        self.assertEqual(db.get_app_state(announcements.LAST_ANNOUNCED_KEY), '2026-11-20')

    def test_no_chats_records_the_release_so_new_users_do_not_get_old_notes(self):
        tmp = os.path.join(self.tmp_dir.name, 'empty.db')
        db.DB_PATH = tmp
        MigrationManager(tmp, migrations_dir=os.path.join(ROOT, 'migrations')).run_migrations()
        self.assertEqual(self.announce(FakeBot()), 0)
        self.assertEqual(db.get_app_state(announcements.LAST_ANNOUNCED_KEY), '2026-11-20')

    def test_no_releases_sends_nothing_and_records_nothing(self):
        bot = FakeBot()
        self.assertEqual(self.announce(bot, []), 0)
        self.assertIsNone(db.get_app_state(announcements.LAST_ANNOUNCED_KEY))


class LoadReleases(unittest.TestCase):
    def load(self, content):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as notes_file:
            notes_file.write(content)
        try:
            return announcements.load_releases(notes_file.name)
        finally:
            os.unlink(notes_file.name)

    def test_malformed_releases_are_skipped(self):
        releases = self.load('''{"releases": [
            {"version": "v4", "notes": ["Bien"]},
            {"version": "v3", "notes": "Texto en vez de lista"},
            {"version": "v2", "notes": []},
            {"version": "", "notes": ["Sin versión"]},
            {"version": "v1", "notes": ["Bien", "  "]},
            "no es un objeto"
        ]}''')
        self.assertEqual([r['version'] for r in releases], ['v4'])

    def test_unreadable_file_means_no_releases(self):
        self.assertEqual(self.load('{ esto no es json'), [])
        self.assertEqual(self.load('{"otra_cosa": []}'), [])


class ReleaseNotesFile(unittest.TestCase):
    """The file shipped with the bot: checked here so a bad edit fails before a deploy."""

    def test_is_valid_and_newest_first(self):
        releases = announcements.load_releases()
        self.assertTrue(releases, 'release_notes.json has no valid release')

        versions = [r['version'] for r in releases]
        self.assertEqual(len(versions), len(set(versions)), 'versions must be unique')
        self.assertEqual(versions, sorted(versions, reverse=True), 'newest release must come first')

        for r in releases:
            with self.subTest(version=r['version']):
                self.assertTrue(all(isinstance(note, str) and note.strip() for note in r['notes']))
                self.assertTrue(all(note.count('`') % 2 == 0 for note in r['notes']), 'unbalanced backticks')

    def test_every_release_fits_in_one_message(self):
        for r in announcements.load_releases():
            with self.subTest(version=r['version']):
                self.assertEqual(len(announcements.format_release_messages([r])), 1)


if __name__ == '__main__':
    unittest.main()
