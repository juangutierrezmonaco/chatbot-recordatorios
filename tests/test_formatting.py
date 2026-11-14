"""Replies that any user text cannot break, and long lists split under Telegram's limit (issue #9).

Run from the project root:
    python3 -m unittest discover -s tests -v
"""
import asyncio
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from html.parser import HTMLParser
from types import SimpleNamespace

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import db  # noqa: E402
import formatting  # noqa: E402
import handlers  # noqa: E402
import scheduler  # noqa: E402
from migrations import MigrationManager  # noqa: E402

TELEGRAM_LIMIT = 4096
ALLOWED_TAGS = {'b', 'i', 'code'}

# Each of these used to break a Markdown reply: unclosed _ * ` [ and HTML characters
NASTY_TEXT = 'Revisar mi_archivo *urgente* `x [link] <tag> & más'


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


class Escaping(unittest.TestCase):
    def test_user_text_is_escaped(self):
        self.assertEqual(formatting.escape('a < b & c > d'), 'a &lt; b &amp; c &gt; d')

    def test_markdown_characters_are_left_alone(self):
        self.assertEqual(formatting.escape('mi_archivo *x* `y` [z]'), 'mi_archivo *x* `y` [z]')

    def test_highlight_any_case_and_escapes_everything(self):
        self.assertEqual(
            formatting.highlight('Vino <tinto> y VINO', 'vino'),
            '<b>Vino</b> &lt;tinto&gt; y <b>VINO</b>'
        )

    def test_highlight_keyword_with_special_characters(self):
        self.assertEqual(formatting.highlight('a+b & c', 'a+b'), '<b>a+b</b> &amp; c')
        self.assertEqual(formatting.highlight('<b>', '<'), '<b>&lt;</b>b&gt;')

    def test_from_markdown_converts_our_own_texts(self):
        self.assertEqual(
            formatting.from_markdown('**Sintaxis:** `/importante <intervalo>` & más'),
            '<b>Sintaxis:</b> <code>/importante &lt;intervalo&gt;</code> &amp; más'
        )


class Splitting(unittest.TestCase):
    def entries(self, count):
        return '📋 <b>Tus recordatorios:</b>\n\n' + ''.join(
            f'🔔 <b>#{i}</b> - 01/12/2026 09:00\n   Recordatorio número {i} ' + 'x' * 80 + '\n\n'
            for i in range(count)
        )

    def test_short_message_is_one_part(self):
        self.assertEqual(formatting.split_message('hola'), ['hola'])
        self.assertEqual(formatting.split_message('  \n '), [])

    def test_long_list_is_split_between_entries(self):
        parts = formatting.split_message(self.entries(60))

        self.assertGreater(len(parts), 1)
        for part in parts:
            self.assertLessEqual(len(part), formatting.MAX_MESSAGE_LENGTH)
            self.assertEqual(html_errors(part), [])
        later_parts = parts[1:]
        self.assertTrue(all(part.startswith('🔔 <b>#') for part in later_parts), 'an entry was cut in two')
        self.assertEqual(sum(part.count('🔔') for part in parts), 60)

    def test_a_single_huge_line_is_cut_at_spaces(self):
        parts = formatting.split_message(' '.join(['palabra'] * 2000), limit=1000)
        self.assertTrue(all(len(part) <= 1000 for part in parts))
        self.assertTrue(all(not part.startswith('alabra') for part in parts))

    def test_a_word_longer_than_the_limit_is_never_cut_inside_an_entity(self):
        text = '&amp;' * 500
        parts = formatting.split_message(text, limit=998)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(part.endswith(';') for part in parts))


class FakeMessage:
    def __init__(self, text=''):
        self.text = text
        self.caption = None
        self.replies = []

    async def reply_text(self, text, parse_mode=None, **kwargs):
        self.replies.append(SimpleNamespace(text=text, parse_mode=parse_mode))


class CommandsWithNastyText(unittest.TestCase):
    """The real handlers, with reminders and notes whose text used to break the reply."""

    CHAT = 1

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        db.DB_PATH = os.path.join(self.tmp_dir.name, 'test.db')
        MigrationManager(db.DB_PATH, migrations_dir=os.path.join(ROOT, 'migrations')).run_migrations()

        timezone = scheduler.TIMEZONE
        self.now = datetime.now(timezone)
        later_today = min(self.now + timedelta(minutes=5),
                          self.now.replace(hour=23, minute=59, second=0, microsecond=0))
        db.add_reminder(self.CHAT, NASTY_TEXT, later_today)
        db.add_reminder(self.CHAT, NASTY_TEXT + ' semana', self.now + timedelta(days=1))
        self.past_id = db.add_reminder(self.CHAT, NASTY_TEXT + ' pasado', self.now - timedelta(days=2))
        db.mark_reminder_sent(self.past_id)
        db.add_vault_entry(self.CHAT, NASTY_TEXT)
        db.create_or_update_user(self.CHAT, first_name='Ana')

    def tearDown(self):
        db.DB_PATH = self.original_db_path
        self.tmp_dir.cleanup()

    def run_command(self, handler, *args, text=''):
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

    def assertSafeReplies(self, replies, must_contain='Revisar mi_archivo *urgente* `x [link] &lt;tag&gt; &amp; más'):
        self.assertTrue(replies, 'no reply')
        for reply in replies:
            self.assertEqual(reply.parse_mode, 'HTML')
            self.assertLessEqual(len(reply.text), TELEGRAM_LIMIT)
            self.assertEqual(html_errors(reply.text), [], reply.text)
        self.assertIn(must_contain, ''.join(reply.text for reply in replies))

    def test_lista(self):
        self.assertSafeReplies(self.run_command(handlers.list_command))

    def test_hoy(self):
        self.assertSafeReplies(self.run_command(handlers.today_command))

    def test_semana_todos(self):
        replies = self.run_command(handlers.week_command, 'todos')
        self.assertEqual(len(replies), 1)
        self.assertEqual(html_errors(replies[0].text), [])

    def test_buscar_highlights_safely(self):
        replies = self.run_command(handlers.search_command, 'mi_archivo')
        self.assertSafeReplies(replies, must_contain='Revisar <b>mi_archivo</b> *urgente*')

    def test_dia_in_the_past(self):
        day = (self.now - timedelta(days=2)).strftime('%d/%m/%Y')
        self.assertSafeReplies(self.run_command(handlers.date_command, day))

    def test_historial(self):
        self.assertSafeReplies(self.run_command(handlers.history_command))

    def test_bitacora_list_and_search(self):
        self.assertSafeReplies(self.run_command(handlers.vault_list_command))
        self.assertSafeReplies(self.run_command(handlers.vault_search_command, 'urgente'),
                               must_contain='Revisar mi_archivo *<b>urgente</b>*')

    def test_averigua_in_natural_language(self):
        self.assertSafeReplies(self.run_command(handlers.free_message, text='averigua urgente'),
                               must_contain='*<b>urgente</b>*')

    def test_important_confirmation(self):
        original = handlers.scheduler.schedule_important_reminder
        handlers.scheduler.schedule_important_reminder = lambda *args: None
        try:
            replies = self.run_command(handlers.important_command,
                                       *f'10 mañana a las 9 {NASTY_TEXT}'.split())
        finally:
            handlers.scheduler.schedule_important_reminder = original
        self.assertSafeReplies(replies)
        self.assertIn('Recordatorio importante creado', replies[0].text)

    def test_explicar(self):
        replies = self.run_command(handlers.explain_command, 'importante')
        self.assertEqual(replies[0].parse_mode, 'HTML')
        self.assertEqual(html_errors(replies[0].text), [])
        self.assertIn('<b>Sintaxis:</b>', replies[0].text)

    def test_a_long_list_comes_in_several_messages(self):
        for i in range(60):
            db.add_reminder(self.CHAT, f'Recordatorio {i} ' + 'y' * 80, self.now + timedelta(days=3, minutes=i))

        replies = self.run_command(handlers.list_command)

        self.assertGreater(len(replies), 1)
        for reply in replies:
            self.assertLessEqual(len(reply.text), TELEGRAM_LIMIT)
            self.assertEqual(html_errors(reply.text), [])


if __name__ == '__main__':
    unittest.main()
