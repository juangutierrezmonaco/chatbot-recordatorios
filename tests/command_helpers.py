"""Shared helpers to run the real command handlers against a temporary database."""
import asyncio
import os
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import db  # noqa: E402
from migrations import MigrationManager  # noqa: E402

TELEGRAM_LIMIT = 4096
ALLOWED_TAGS = {'b', 'i', 'code'}


class TelegramHtmlChecker(HTMLParser):
    """Fails on tags Telegram does not accept here, or that are not closed on time."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.open_tags = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED_TAGS:
            self.errors.append(f'unexpected tag <{tag}>')
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if not self.open_tags or self.open_tags.pop() != tag:
            self.errors.append(f'unbalanced </{tag}>')

    def handle_entityref(self, name):
        if name not in ('lt', 'gt', 'amp', 'quot'):
            self.errors.append(f'unknown entity &{name};')


def html_errors(text):
    checker = TelegramHtmlChecker()
    checker.feed(text)
    checker.close()
    if checker.open_tags:
        checker.errors.append(f'unclosed {checker.open_tags}')
    return checker.errors


class FakeMessage:
    def __init__(self, text=''):
        self.text = text
        self.caption = None
        self.replies = []

    async def reply_text(self, text, parse_mode=None, **kwargs):
        self.replies.append(SimpleNamespace(text=text, parse_mode=parse_mode))


class CommandTestCase(unittest.TestCase):
    """A temporary database with every migration, and a way to run a handler as chat CHAT."""

    CHAT = 1

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tmp_dir.name, 'test.db')
        MigrationManager(db.DB_PATH, migrations_dir=os.path.join(ROOT, 'migrations')).run_migrations()
        db.create_or_update_user(self.CHAT, first_name='Ana')

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tmp_dir.cleanup()

    def run_command(self, handler, *args, text=''):
        """Replies of the handler, as a list with .text and .parse_mode."""
        message = FakeMessage(text)
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(id=self.CHAT, type='private'),
            effective_user=SimpleNamespace(id=self.CHAT, username=None, first_name='Ana',
                                           last_name=None, is_bot=False, language_code='es'),
            message=message
        )
        context = SimpleNamespace(args=list(args), user_data={}, bot=None)
        asyncio.run(handler(update, context))
        return message.replies

    def reply_text(self, handler, *args, text=''):
        """All replies joined, checking each one is valid HTML (or plain text) under the limit."""
        replies = self.run_command(handler, *args, text=text)
        self.assertTrue(replies, 'no reply')
        for reply in replies:
            self.assertLessEqual(len(reply.text), TELEGRAM_LIMIT)
            if reply.parse_mode == 'HTML':
                self.assertEqual(html_errors(reply.text), [], reply.text)
        return '\n'.join(reply.text for reply in replies)
