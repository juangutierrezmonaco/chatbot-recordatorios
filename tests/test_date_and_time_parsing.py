"""Date and time written in the same message (issue #3).

Run from the project root:
    python3 -m unittest discover -s tests -v
"""
import unittest
from datetime import datetime

from parsing_helpers import TZ, ParsingCases, at

WITH_YEAR = '%d/%m/%Y %H:%M'


class WeekdayWithTime(ParsingCases):
    """'now' is Wednesday 11/11/2026 at 15:00 unless stated otherwise."""

    def test_weekday_next_to_the_time(self):
        self.check([
            ('el viernes a las 10 reunión', ('13/11 10:00', 'reunión')),
            ('viernes a las 18 reunión', ('13/11 18:00', 'reunión')),
            ('reunión el viernes a las 10', ('13/11 10:00', 'reunión')),
            ('a las 10 el viernes reunión', ('13/11 10:00', 'reunión')),
            ('el viernes reunión a las 10', ('13/11 10:00', 'reunión')),
            ('el jueves a las 9 de la noche cine', ('12/11 21:00', 'cine')),
            ('el lunes a las 8.30hs standup', ('16/11 08:30', 'standup')),
        ], at(15))

    def test_weekday_with_accent(self):
        self.check([
            ('el sábado a las 10 ir a la feria', ('14/11 10:00', 'ir a la feria')),
            ('el sabado a las 10 ir a la feria', ('14/11 10:00', 'ir a la feria')),
            ('el miércoles a las 20 fútbol', ('11/11 20:00', 'fútbol')),
        ], at(15))

    def test_todays_weekday_means_today_while_the_time_is_ahead(self):
        self.check([
            ('el miércoles a las 20 fútbol', ('11/11 20:00', 'fútbol')),
            # A weekday name keeps the hour as written: 10:00 passed, so next week's Wednesday
            ('el miércoles a las 10 fútbol', ('18/11 10:00', 'fútbol')),
            ('el miércoles a las 14 fútbol', ('18/11 14:00', 'fútbol')),
        ], at(15))

    def test_next_week_qualifiers(self):
        self.check([
            ('el miércoles que viene a las 20 fútbol', ('18/11 20:00', 'fútbol')),
            ('el próximo miércoles a las 20 fútbol', ('18/11 20:00', 'fútbol')),
            ('el lunes que viene a las 9 reunión', ('16/11 09:00', 'reunión')),
            ('el próximo viernes a las 10 reunión', ('13/11 10:00', 'reunión')),
        ], at(15))

    def test_weekday_inside_the_reminder_stays_in_the_text(self):
        self.check([
            ('a las 20 avisar que el viernes no voy', ('11/11 20:00', 'avisar que el viernes no voy')),
        ], at(15))


class FullDates(ParsingCases):
    def test_numeric_date_with_year(self):
        self.check([
            ('20/12/2026 09:30 viaje', ('20/12/2026 09:30', 'viaje')),
            ('20/12/26 9:30 viaje', ('20/12/2026 09:30', 'viaje')),
            ('el 20/12/2026 a las 9 viaje', ('20/12/2026 09:00', 'viaje')),
            ('20-12-2026 18hs viaje', ('20/12/2026 18:00', 'viaje')),
            ('20/12/2026 viaje', ('20/12/2026 09:00', 'viaje')),
            ('05/01/2027 10:15 volver', ('05/01/2027 10:15', 'volver')),
        ], at(15), WITH_YEAR)

    def test_a_past_date_with_year_is_kept_as_written(self):
        # The caller answers "La fecha debe ser en el futuro" instead of moving it a year ahead
        self.check([
            ('10/11/2026 10:00 algo', ('10/11/2026 10:00', 'algo')),
        ], at(15), WITH_YEAR)

    def test_numeric_date_without_year(self):
        self.check([
            ('20/12 09:30 viaje', ('20/12/2026 09:30', 'viaje')),
            ('el 20/12 21:15 viaje', ('20/12/2026 21:15', 'viaje')),
            ('20/12 18hs viaje', ('20/12/2026 18:00', 'viaje')),
            ('05/01 9:30 volver', ('05/01/2027 09:30', 'volver')),
        ], at(15), WITH_YEAR)

    def test_clock_notation_is_never_moved_to_the_afternoon(self):
        self.check([
            ('20/12 3:30 salir al aeropuerto', ('20/12 03:30', 'salir al aeropuerto')),
            ('20/12 3:30 pm salir al aeropuerto', ('20/12 15:30', 'salir al aeropuerto')),
        ], at(15))

    def test_month_name(self):
        self.check([
            ('el 25 de diciembre a las 10 abrir regalos', ('25/12/2026 10:00', 'abrir regalos')),
            ('25 de diciembre abrir regalos', ('25/12/2026 09:00', 'abrir regalos')),
            ('25 de diciembre 20:30 cena', ('25/12/2026 20:30', 'cena')),
            ('el 5 de enero a las 8 volver al trabajo', ('05/01/2027 08:00', 'volver al trabajo')),
            ('25 de diciembre de 2027 a las 10 abrir regalos', ('25/12/2027 10:00', 'abrir regalos')),
            ('el 21 de setiembre a las 11 picnic', ('21/09/2027 11:00', 'picnic')),
        ], at(15), WITH_YEAR)

    def test_month_name_away_from_the_start_needs_el_or_a_time(self):
        self.check([
            ('abrir regalos el 25 de diciembre', ('25/12/2026 09:00', 'abrir regalos')),
            ('abrir regalos 25 de diciembre a las 10', ('25/12/2026 10:00', 'abrir regalos')),
            ('abrir regalos 25 de diciembre 20:30', ('25/12/2026 20:30', 'abrir regalos')),
        ], at(15), WITH_YEAR)

    def test_street_names_are_not_dates(self):
        self.check([
            ('mañana a las 10 ir a 9 de julio 1234', ('12/11/2026 10:00', 'ir a 9 de julio 1234')),
            ('el viernes a las 10 ir a 25 de mayo 300', ('13/11/2026 10:00', 'ir a 25 de mayo 300')),
            ('a las 18 pasar por 1 de mayo y corrientes', ('11/11/2026 18:00', 'pasar por 1 de mayo y corrientes')),
        ], at(15), WITH_YEAR)

    def test_only_20xx_is_read_as_a_year(self):
        self.check([
            ('25 de diciembre 1234 brindar', ('25/12/2026 09:00', '1234 brindar')),
        ], at(15), WITH_YEAR)

    def test_weekday_said_with_a_full_date_is_dropped(self):
        # The date already tells the day, so the weekday must not stay in the reminder text
        self.check([
            ('viernes 25 de diciembre a las 10 abrir regalos', ('25/12/2026 10:00', 'abrir regalos')),
            ('abrir regalos el viernes 25 de diciembre', ('25/12/2026 09:00', 'abrir regalos')),
            ('el domingo 20/12/2026 09:30 viaje', ('20/12/2026 09:30', 'viaje')),
            ('domingo 20/12 a las 10 viaje', ('20/12/2026 10:00', 'viaje')),
            ('el domingo 20/12 18hs viaje', ('20/12/2026 18:00', 'viaje')),
        ], at(15), WITH_YEAR)


class DayAfterTomorrow(ParsingCases):
    def test_with_and_without_time(self):
        self.check([
            ('pasado mañana llamar a mamá', ('13/11 09:00', 'llamar a mamá')),
            ('pasado mañana 18:00 llamar a mamá', ('13/11 18:00', 'llamar a mamá')),
            ('pasado mañana 18hs llamar a mamá', ('13/11 18:00', 'llamar a mamá')),
            ('pasado mañana a las 10 llamar a mamá', ('13/11 10:00', 'llamar a mamá')),
            ('llamar a mamá pasado mañana', ('13/11 09:00', 'llamar a mamá')),
        ], at(15))


class RelativeOffsetsComeFirst(ParsingCases):
    def test_en_x_wins_over_a_day_mentioned_in_the_text(self):
        self.check([
            ('en 2 horas avisar que pasado mañana no voy', ('11/11 17:00', 'avisar que pasado mañana no voy')),
            ('en 30 minutos llamar para el turno de mañana 18:00', ('11/11 15:30', 'llamar para el turno de mañana 18:00')),
        ], at(15))


class NamedDayWithClockTime(ParsingCases):
    def test_clock_time_next_to_a_named_day(self):
        self.check([
            ('mañana 18:00 comprar comida', ('12/11 18:00', 'comprar comida')),
            ('comprar comida mañana 18:00', ('12/11 18:00', 'comprar comida')),
            ('hoy 18:30 cenar', ('11/11 18:30', 'cenar')),
            ('el viernes 18:00 reunión', ('13/11 18:00', 'reunión')),
            ('viernes 18hs reunión', ('13/11 18:00', 'reunión')),
            ('el sábado 9:30 feria', ('14/11 09:30', 'feria')),
            ('18:00 mañana comprar comida', ('12/11 18:00', 'comprar comida')),
            ('mañana 6:30 pm gimnasio', ('12/11 18:30', 'gimnasio')),
        ], at(15))

    def test_numbers_away_from_the_day_are_not_a_time(self):
        self.check([
            ('pasado mañana comprar 2 hs de estacionamiento', ('13/11 09:00', 'comprar 2 hs de estacionamiento')),
            ('20/12 comprar 2 hs de estacionamiento', ('20/12 09:00', 'comprar 2 hs de estacionamiento')),
            ('el 25 de diciembre brindar 00:00', ('25/12 09:00', 'brindar 00:00')),
        ], at(15))

    def test_weekday_plus_clock_time_is_not_read_as_a_day_of_the_month(self):
        # On Monday 14/12/2026 the 18th is a Friday: "viernes 18:00" is a time, not "Friday the 18th"
        monday = TZ.localize(datetime(2026, 12, 14, 15, 0))
        self.check([
            ('viernes 18:00 reunión', ('18/12 18:00', 'reunión')),
            ('viernes 18hs reunión', ('18/12 18:00', 'reunión')),
            ('viernes 18 hs reunión', ('18/12 18:00', 'reunión')),
            ('viernes 18 a las 20 reunión', ('18/12 20:00', 'reunión')),
        ], monday)


if __name__ == '__main__':
    unittest.main()
