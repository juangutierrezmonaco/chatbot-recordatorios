"""Commands that show reminders: /dia, /hoy, /semana, /historial and /buscar (issue #8).

Run from the project root:
    python3 -m unittest discover -s tests -v
"""
import sqlite3
import unittest
from datetime import datetime, timedelta

from command_helpers import CommandTestCase

import db  # noqa: E402
import handlers  # noqa: E402
import scheduler  # noqa: E402


class QueryCommandsTestCase(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.now = datetime.now(scheduler.TIMEZONE)

    def at_noon(self, days_from_today):
        day = self.now + timedelta(days=days_from_today)
        return day.replace(hour=12, minute=0, second=0, microsecond=0)

    def reminder(self, text, when, status='active', important=False):
        if important:
            reminder_id = db.add_important_reminder(self.CHAT, text, when, repeat_interval=10)
        else:
            reminder_id = db.add_reminder(self.CHAT, text, when)
        if status != 'active':
            with sqlite3.connect(db.DB_PATH) as conn:
                conn.execute('UPDATE reminders SET status = ? WHERE id = ?', (status, reminder_id))
        return reminder_id


class DayCommand(QueryCommandsTestCase):
    def test_tomorrow_with_a_reminder_no_longer_fails(self):
        self.reminder('Dentista', self.at_noon(1))

        text = self.reply_text(handlers.date_command, 'mañana')

        self.assertIn('Recordatorios para el', text)
        self.assertIn('Dentista', text)
        self.assertIn('12:00', text)

    def test_shows_the_status_of_each_reminder(self):
        day = self.at_noon(-3)
        self.reminder('Enviado', day, status='sent')
        self.reminder('Hecho', day + timedelta(minutes=5), status='completed')
        self.reminder('No llegó', day + timedelta(minutes=10), status='failed')
        self.reminder('Cancelado', day + timedelta(minutes=15), status='cancelled')

        text = self.reply_text(handlers.date_command, day.strftime('%d/%m/%Y'))

        self.assertIn('✅', text)
        self.assertIn('(enviado)', text)
        self.assertIn('🏁', text)
        self.assertIn('(completado)', text)
        self.assertIn('(no se pudo enviar)', text)
        self.assertNotIn('Cancelado', text, 'cancelled reminders are in /historial cancelados')

    def test_important_reminders_are_marked(self):
        self.reminder('Pastilla', self.at_noon(2), important=True)
        text = self.reply_text(handlers.date_command, self.at_noon(2).strftime('%d/%m/%Y'))
        self.assertIn('🔥', text)

    def test_today_shows_the_same_as_hoy(self):
        later_today = min(self.now + timedelta(minutes=5),
                          self.now.replace(hour=23, minute=59, second=0, microsecond=0))
        earlier_today = self.now.replace(hour=0, minute=1, second=0, microsecond=0)
        self.reminder('Pendiente', later_today)
        self.reminder('Ya enviado', earlier_today, status='sent')

        day_text = self.reply_text(handlers.date_command, 'hoy')
        today_text = self.reply_text(handlers.today_command)

        for text in (day_text, today_text):
            self.assertIn('Pendiente', text)
            self.assertIn('Ya enviado', text)
        self.assertEqual(day_text.split('\n\n', 1)[1], today_text.split('\n\n', 1)[1])

    def test_a_day_without_reminders(self):
        text = self.reply_text(handlers.date_command, 'mañana')
        self.assertIn('No tienes recordatorios para el', text)

    def test_a_date_saved_without_timezone_shows_its_own_hour(self):
        reminder_id = self.reminder('Viejo', self.at_noon(1))
        naive = self.at_noon(1).replace(hour=9, tzinfo=None).isoformat()
        with sqlite3.connect(db.DB_PATH) as conn:
            conn.execute('UPDATE reminders SET datetime = ? WHERE id = ?', (naive, reminder_id))

        text = self.reply_text(handlers.date_command, 'mañana')

        self.assertIn('09:00', text)


class TodayCommand(QueryCommandsTestCase):
    def test_marks_important_and_completed_reminders(self):
        later_today = min(self.now + timedelta(minutes=5),
                          self.now.replace(hour=23, minute=59, second=0, microsecond=0))
        self.reminder('Pastilla', later_today, important=True)
        self.reminder('Hecho', later_today, status='completed')
        self.reminder('Cancelado', later_today, status='cancelled')

        text = self.reply_text(handlers.today_command)

        self.assertIn('🔥', text)
        self.assertIn('Pastilla', text)
        self.assertIn('🏁', text)
        self.assertNotIn('Cancelado', text)


class WeekCommand(QueryCommandsTestCase):
    def test_pendientes_is_accepted_as_the_documentation_says(self):
        self.reminder('Dentista', self.now + timedelta(minutes=1))
        text = self.reply_text(handlers.week_command, 'pendientes')
        self.assertNotIn('Uso', text)
        self.assertIn('pendientes de esta semana', text)

    def test_an_unknown_argument_shows_the_usage(self):
        self.assertIn('/semana todos', self.reply_text(handlers.week_command, 'mañana'))

    def test_todos_includes_sent_and_completed(self):
        monday = (self.now - timedelta(days=self.now.weekday())).replace(hour=0, minute=30, second=0, microsecond=0)
        self.reminder('Enviado', monday, status='sent')
        self.reminder('Hecho', monday + timedelta(minutes=1), status='completed')

        pending = self.reply_text(handlers.week_command)
        everything = self.reply_text(handlers.week_command, 'todos')

        self.assertNotIn('Enviado', pending)
        self.assertIn('Enviado', everything)
        self.assertIn('Hecho', everything)


class HistoryCommand(QueryCommandsTestCase):
    def setUp(self):
        super().setUp()
        for i in range(30):
            self.reminder(f'Enviado {i}', self.at_noon(-40 + i), status='sent')
        self.reminder('Completado', self.at_noon(-2), status='completed')
        self.reminder('Cancelado', self.at_noon(-2), status='cancelled')
        self.reminder('Fallido', self.at_noon(-2), status='failed')

    def test_completed_reminders_are_visible(self):
        self.assertIn('Completado', self.reply_text(handlers.history_command))
        text = self.reply_text(handlers.history_command, 'completados')
        self.assertIn('Recordatorios completados', text)
        self.assertNotIn('Enviado', text)

    def test_how_many_to_show(self):
        self.assertEqual(self.reply_text(handlers.history_command).count('#'), 20)
        self.assertEqual(self.reply_text(handlers.history_command, '25').count('#'), 25)
        self.assertEqual(self.reply_text(handlers.history_command, 'enviados', '3').count('#'), 3)

    def test_the_limit_is_capped(self):
        text = self.reply_text(handlers.history_command, '5000')
        self.assertEqual(text.count('#'), 33)

    def test_suggests_how_to_see_more(self):
        self.assertIn('/historial 100', self.reply_text(handlers.history_command))

    def test_an_unknown_argument_shows_the_usage(self):
        self.assertIn('/historial completados', self.reply_text(handlers.history_command, 'ayer'))


class SearchCommand(QueryCommandsTestCase):
    def test_finds_pending_and_finished_reminders(self):
        self.reminder('Llamar al dentista', self.at_noon(3))
        self.reminder('Turno con el dentista', self.at_noon(-10), status='sent')
        self.reminder('Pagar luz', self.at_noon(-10), status='sent')

        text = self.reply_text(handlers.search_command, 'dentista')

        self.assertIn('Llamar al <b>dentista</b>', text)
        self.assertIn('En el historial', text)
        self.assertIn('Turno con el <b>dentista</b>', text)
        self.assertIn('(enviado)', text)
        self.assertNotIn('Pagar luz', text)

    def test_a_term_found_only_in_the_history(self):
        self.reminder('Comprar regalo', self.at_noon(-5), status='completed')

        text = self.reply_text(handlers.search_command, 'regalo')

        self.assertIn('Ninguno pendiente', text)
        self.assertIn('(completado)', text)

    def test_history_results_are_limited(self):
        for i in range(15):
            self.reminder(f'Gimnasio {i}', self.at_noon(-30 + i), status='sent')
        text = self.reply_text(handlers.search_command, 'gimnasio')
        self.assertEqual(text.count('Gimnasio'), handlers.SEARCH_HISTORY_LIMIT)

    def test_nothing_found(self):
        self.assertIn('No se encontraron', self.reply_text(handlers.search_command, 'inexistente'))


if __name__ == '__main__':
    unittest.main()
