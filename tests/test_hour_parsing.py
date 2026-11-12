"""Hour interpretation in reminders (issue #2).

Run from the project root:
    python3 -m unittest discover -s tests -v
"""
import unittest

from parsing_helpers import ParsingCases as HourCases, at, extract_date_and_text


class NoonAndMidnight(HourCases):
    def test_twelve_is_noon(self):
        self.check([
            ('recordame a las 12 almorzar', ('12/11 12:00', 'almorzar')),
            ('a las 12:30 llamar', ('12/11 12:30', 'llamar')),
            ('mañana a las 12 almorzar', ('12/11 12:00', 'almorzar')),
            ('a las 12 del mediodía almorzar', ('12/11 12:00', 'almorzar')),
            ('a las 12 pm almorzar', ('12/11 12:00', 'almorzar')),
            ('a las 12 de la mañana almorzar', ('12/11 12:00', 'almorzar')),
        ], at(15))

    def test_twelve_in_the_morning_is_today(self):
        self.check([
            ('a las 12 almorzar', ('11/11 12:00', 'almorzar')),
            ('hoy a las 12 almorzar', ('11/11 12:00', 'almorzar')),
        ], at(9))

    def test_midnight_has_to_be_explicit(self):
        self.check([
            ('a las 12 de la noche apagar todo', ('12/11 00:00', 'apagar todo')),
            ('a las 0 apagar todo', ('12/11 00:00', 'apagar todo')),
            ('a las 0:30 apagar el horno', ('12/11 00:30', 'apagar el horno')),
            ('a las 12 am apagar todo', ('12/11 00:00', 'apagar todo')),
            # The midnight that closes tomorrow
            ('mañana a las 12 de la noche apagar todo', ('13/11 00:00', 'apagar todo')),
        ], at(15))

    def test_zero_hour_is_never_noon(self):
        self.check([
            ('a las 0:30 apagar el horno', ('12/11 00:30', 'apagar el horno')),
        ], at(9))


class ExplicitPeriod(HourCases):
    def test_spanish_periods(self):
        self.check([
            ('a las 9 de la noche tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 9 de la mañana tomar pastilla', ('12/11 09:00', 'tomar pastilla')),
            ('a las 4 de la tarde merendar', ('11/11 16:00', 'merendar')),
            ('a las 3 de la tarde merendar', ('12/11 15:00', 'merendar')),
            ('a las 5 de la madrugada salir', ('12/11 05:00', 'salir')),
            ('a las 9 por la noche tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 1 del mediodía almorzar', ('12/11 13:00', 'almorzar')),
            ('mañana a las 9 de la noche tomar pastilla', ('12/11 21:00', 'tomar pastilla')),
            ('mañana a las 10 de la mañana ir al médico', ('12/11 10:00', 'ir al médico')),
        ], at(15))

    def test_am_pm(self):
        self.check([
            ('a las 9 pm tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 9pm tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 9 p.m. tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 9 AM tomar pastilla', ('12/11 09:00', 'tomar pastilla')),
            ('a las 9:15 a. m. tomar pastilla', ('12/11 09:15', 'tomar pastilla')),
        ], at(15))

    def test_period_is_ignored_on_24h_hours(self):
        self.check([
            ('a las 21 de la noche tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
        ], at(15))

    def test_words_starting_like_a_period_stay_in_the_text(self):
        self.check([
            ('a las 9 ampliar el plazo', ('11/11 21:00', 'ampliar el plazo')),
            ('a las 9 a mi mamá llamar', ('11/11 21:00', 'a mi mamá llamar')),
            ('a las 9 hacer la tarea', ('11/11 21:00', 'hacer la tarea')),
        ], at(15))


class MinutesAndSuffixes(HourCases):
    def test_formats(self):
        self.check([
            ('a las 9.30 standup', ('11/11 21:30', 'standup')),
            ('a las 9:30 standup', ('11/11 21:30', 'standup')),
            ('a las 21hs tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 21 hs tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 21.30hs tomar pastilla', ('11/11 21:30', 'tomar pastilla')),
            ('a las 21 horas tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('a las 21h tomar pastilla', ('11/11 21:00', 'tomar pastilla')),
            ('mañana a las 21hs tomar pastilla', ('12/11 21:00', 'tomar pastilla')),
        ], at(15))


class AmbiguousHour(HourCases):
    """1-11 with no hint and no day: the next time the clock shows that hour."""

    def test_next_occurrence_in_the_afternoon(self):
        self.check([
            ('a las 10 llamar', ('11/11 22:00', 'llamar')),
            ('a las 4 llamar', ('11/11 16:00', 'llamar')),
            ('a las 3 llamar', ('12/11 03:00', 'llamar')),
            ('a las 18 llamar', ('11/11 18:00', 'llamar')),
            ('a las 14 llamar', ('12/11 14:00', 'llamar')),
        ], at(15))

    def test_next_occurrence_in_the_morning(self):
        self.check([
            ('a las 10 llamar', ('11/11 10:00', 'llamar')),
            ('a las 8 desayuno', ('11/11 20:00', 'desayuno')),
            ('a las 8 de la mañana desayuno', ('12/11 08:00', 'desayuno')),
        ], at(9))

    def test_next_occurrence_late_at_night(self):
        self.check([
            ('a las 7 despertarme', ('12/11 07:00', 'despertarme')),
            ('a las 11:45 dormir', ('11/11 23:45', 'dormir')),
        ], at(23, 30))


class HourOnAGivenDay(HourCases):
    def test_today(self):
        self.check([
            ('hoy a las 8 cenar', ('11/11 20:00', 'cenar')),
            ('hoy a las 20 cenar', ('11/11 20:00', 'cenar')),
            ('hoy a las 5 merendar', ('11/11 17:00', 'merendar')),
        ], at(15))

    def test_today_keeps_the_day_even_if_the_hour_passed(self):
        # The caller answers "La fecha debe ser en el futuro" instead of moving it to tomorrow
        self.check([
            ('hoy a las 14 almorzar', ('11/11 14:00', 'almorzar')),
            ('hoy a las 2 almorzar', ('11/11 14:00', 'almorzar')),
        ], at(15))

    def test_another_day_takes_the_hour_as_written(self):
        # 1-11 are the morning; the afternoon needs 13-23 or a hint
        self.check([
            ('mañana a las 10 ir al médico', ('12/11 10:00', 'ir al médico')),
            ('mañana a las 7 gimnasio', ('12/11 07:00', 'gimnasio')),
            ('mañana a las 6 levantarme', ('12/11 06:00', 'levantarme')),
            ('mañana a las 3 tomar antibiótico', ('12/11 03:00', 'tomar antibiótico')),
            ('mañana a las 15 merendar', ('12/11 15:00', 'merendar')),
            ('mañana a las 3 de la tarde merendar', ('12/11 15:00', 'merendar')),
            ('pasado mañana a las 10 llamar a mamá', ('13/11 10:00', 'llamar a mamá')),
        ], at(15))

    def test_after_a_date(self):
        self.check([
            ('el 20/12 a las 9 viaje', ('20/12 09:00', 'viaje')),
            ('el 20/12 a las 3 viaje', ('20/12 03:00', 'viaje')),
            ('el 20/12 a las 15 viaje', ('20/12 15:00', 'viaje')),
            ('el 20/12 a las 9 de la noche viaje', ('20/12 21:00', 'viaje')),
            ('el 20/12 a las 9.30hs viaje', ('20/12 09:30', 'viaje')),
            ('el 20/12 a las 12 viaje', ('20/12 12:00', 'viaje')),
            ('lunes 16 a las 8 reunión', ('16/11 08:00', 'reunión')),
        ], at(15))


class DayWordPosition(HourCases):
    """hoy / mañana count as the day only next to the time or opening the message."""

    def test_day_word_tied_to_the_time(self):
        self.check([
            ('mañana a las 10 ir al médico', ('12/11 10:00', 'ir al médico')),
            ('ir al médico mañana a las 10', ('12/11 10:00', 'ir al médico')),
            ('a las 10 mañana ir al médico', ('12/11 10:00', 'ir al médico')),
            ('mañana ir al médico a las 10', ('12/11 10:00', 'ir al médico')),
            ('ir al médico pasado mañana a las 10', ('13/11 10:00', 'ir al médico')),
        ], at(15))

    def test_day_word_inside_the_reminder_stays_in_the_text(self):
        # "que" and "de" are dropped by the request-word cleanup (issue #5)
        self.check([
            ('a las 20 avisar que mañana no voy', ('11/11 20:00', 'avisar mañana no voy')),
            ('a las 18 comprar pan para hoy y mañana', ('11/11 18:00', 'comprar pan para hoy y mañana')),
            ('a las 9 llamar para confirmar el turno de mañana', ('11/11 21:00', 'llamar para confirmar el turno mañana')),
        ], at(15))


class InvalidHour(HourCases):
    def test_does_not_crash(self):
        for text in ('a las 25 algo', 'a las 9:75 algo', 'a las 99 algo'):
            with self.subTest(text=text):
                extract_date_and_text(text, now=at(15))


if __name__ == '__main__':
    unittest.main()
