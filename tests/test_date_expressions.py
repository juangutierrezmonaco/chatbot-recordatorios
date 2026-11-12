"""Date expressions that were not recognized or were misread (issue #4).

Run from the project root:
    python3 -m unittest discover -s tests -v

'now' is Wednesday 11/11/2026 at 15:00 unless stated otherwise.
"""
import unittest
from datetime import datetime

from parsing_helpers import TZ, ParsingCases, at, parse

WITH_YEAR = '%d/%m/%Y %H:%M'
WITH_SECONDS = '%d/%m %H:%M:%S'


class RelativeOffsets(ParsingCases):
    def test_months_are_not_minutes(self):
        self.check([
            ('en 2 meses renovar el pasaporte', ('11/01/2027 15:00', 'renovar el pasaporte')),
            ('en un mes pagar la cuota', ('11/12/2026 15:00', 'pagar la cuota')),
            ('en 1 año renovar el dominio', ('11/11/2027 15:00', 'renovar el dominio')),
            ('en 5 mesas servir el postre', (None, None)),
        ], at(15), WITH_YEAR)

    def test_month_offset_is_capped_to_the_length_of_the_month(self):
        january_31 = TZ.localize(datetime(2027, 1, 31, 10, 0))
        self.check([
            ('en 1 mes pagar', ('28/02/2027 10:00', 'pagar')),
        ], january_31, WITH_YEAR)

    def test_days_and_weeks(self):
        self.check([
            ('en 3 días llamar al banco', ('14/11 15:00', 'llamar al banco')),
            ('en 3 dias llamar al banco', ('14/11 15:00', 'llamar al banco')),
            ('en un día llamar al banco', ('12/11 15:00', 'llamar al banco')),
            ('en 2 semanas pagar la tarjeta', ('25/11 15:00', 'pagar la tarjeta')),
            ('en una semana pagar la tarjeta', ('18/11 15:00', 'pagar la tarjeta')),
        ], at(15))

    def test_hours_minutes_and_seconds(self):
        self.check([
            ('en 45 minutos sacar la pizza', ('11/11 15:45:00', 'sacar la pizza')),
            ('en 30m sacar la pizza', ('11/11 15:30:00', 'sacar la pizza')),
            ('en 5 min sacar la pizza', ('11/11 15:05:00', 'sacar la pizza')),
            ('en 2 horas llamar', ('11/11 17:00:00', 'llamar')),
            ('en 2h llamar', ('11/11 17:00:00', 'llamar')),
            ('en 2 hs llamar', ('11/11 17:00:00', 'llamar')),
            ('en media hora llamar', ('11/11 15:30:00', 'llamar')),
            ('en una hora y media sacar la pizza', ('11/11 16:30:00', 'sacar la pizza')),
            ('en 2 horas y media sacar la pizza', ('11/11 17:30:00', 'sacar la pizza')),
            ('en 90 segundos mirar el horno', ('11/11 15:01:30', 'mirar el horno')),
            ('en un minuto y medio mirar el horno', ('11/11 15:01:30', 'mirar el horno')),
        ], at(15), WITH_SECONDS)

    def test_words_that_only_start_like_a_unit(self):
        self.check([
            ('en 2 hamburguesas pensar', (None, None)),
            ('en 3 documentos firmar', (None, None)),
        ], at(15))

    def test_day_offset_with_a_time(self):
        self.check([
            ('en 3 días a las 10 llamar al banco', ('14/11 10:00', 'llamar al banco')),
            ('en 2 semanas a las 9 de la noche cena', ('25/11 21:00', 'cena')),
            ('en 3 días 18:00 llamar al banco', ('14/11 18:00', 'llamar al banco')),
            ('en 3 días a la tarde llamar al banco', ('14/11 16:00', 'llamar al banco')),
        ], at(15))

    def test_half_months_and_years(self):
        self.check([
            ('en un mes y medio pagar la cuota', ('26/12/2026 15:00', 'pagar la cuota')),
            ('en medio mes pagar la cuota', ('26/11/2026 15:00', 'pagar la cuota')),
            ('en un año y medio renovar', ('11/05/2028 15:00', 'renovar')),
        ], at(15), WITH_YEAR)

    def test_a_day_named_first_wins_over_a_day_offset_in_the_text(self):
        # "que" is dropped by the request-word cleanup (issue #5)
        self.check([
            ('mañana avisar que en 2 semanas viajo', ('12/11 09:00', 'avisar en 2 semanas viajo')),
            ('el viernes avisar que en 3 meses vence el contrato', ('13/11 09:00', 'avisar en 3 meses vence el contrato')),
            ('mañana a las 10 avisar que en 2 semanas viajo', ('12/11 10:00', 'avisar en 2 semanas viajo')),
            # The offset comes first: it is the date
            ('en 2 semanas avisar que mañana no voy', ('25/11 15:00', 'avisar mañana no voy')),
            # Minutes and hours always count from now
            ('hoy llamar en 30 minutos a Juan', ('11/11 15:30', 'hoy llamar a Juan')),
        ], at(15))


class WeekdayWithoutTime(ParsingCases):
    def test_weekday_alone_is_at_nine(self):
        self.check([
            ('el sábado ir a la feria', ('14/11 09:00', 'ir a la feria')),
            ('el viernes comprar cerveza', ('13/11 09:00', 'comprar cerveza')),
            ('viernes comprar cerveza', ('13/11 09:00', 'comprar cerveza')),
            ('comprar cerveza el viernes', ('13/11 09:00', 'comprar cerveza')),
            ('el miércoles reunión', ('18/11 09:00', 'reunión')),
        ], at(15))

    def test_next_week_qualifiers(self):
        self.check([
            ('sábado que viene ir a la feria', ('14/11 09:00', 'ir a la feria')),
            ('el lunes que viene reunión', ('16/11 09:00', 'reunión')),
            ('el miércoles que viene reunión', ('18/11 09:00', 'reunión')),
            ('el próximo martes dentista', ('17/11 09:00', 'dentista')),
        ], at(15))

    def test_todays_weekday_in_the_morning_is_today(self):
        self.check([
            ('el miércoles reunión', ('11/11 09:00', 'reunión')),
        ], at(8))

    def test_weekday_with_day_number_and_accent(self):
        self.check([
            ('miércoles 18 turno', ('18/11 09:00', 'turno')),
            ('el sábado 14 a las 10 feria', ('14/11 10:00', 'feria')),
            ('sábado 14 feria', ('14/11 09:00', 'feria')),
        ], at(15))


class RelativeDayWithoutTime(ParsingCases):
    def test_tomorrow_and_today(self):
        self.check([
            ('mañana comprar pan', ('12/11 09:00', 'comprar pan')),
            ('comprar pan mañana', ('12/11 09:00', 'comprar pan')),
            ('pasado mañana llamar a mamá', ('13/11 09:00', 'llamar a mamá')),
            # Today at 9 already passed: the caller answers that the date must be in the future
            ('hoy comprar pan', ('11/11 09:00', 'comprar pan')),
        ], at(15))

    def test_a_date_with_nothing_else_gets_a_default_name(self):
        self.check([
            ('mañana', ('12/11 09:00', 'recordatorio')),
            ('mañana 18:00', ('12/11 18:00', 'recordatorio')),
            ('el viernes', ('13/11 09:00', 'recordatorio')),
            ('esta noche', ('11/11 21:00', 'recordatorio')),
        ], at(15))

    def test_a_time_with_minutes_away_from_the_day_is_not_ignored(self):
        # Not understood rather than silently moved to 09:00
        now = at(15)
        for text in ('el lunes reunión con Juan 15:30', 'el sábado partido 21:00'):
            with self.subTest(text=text):
                parsed, _ = parse(text, now)
                self.assertNotIn('09:00', parsed or '')


class MomentOfDay(ParsingCases):
    def test_named_day_with_a_part_of_the_day(self):
        self.check([
            ('mañana a la tarde llamar al plomero', ('12/11 16:00', 'llamar al plomero')),
            ('llamar al plomero mañana a la tarde', ('12/11 16:00', 'llamar al plomero')),
            ('mañana a la mañana ir al banco', ('12/11 09:00', 'ir al banco')),
            ('mañana por la noche cine', ('12/11 21:00', 'cine')),
            ('mañana al mediodía almorzar con ana', ('12/11 12:00', 'almorzar con ana')),
            ('el viernes a la noche cine', ('13/11 21:00', 'cine')),
            ('el sábado a la mañana feria', ('14/11 09:00', 'feria')),
            ('hoy a la noche sacar la basura', ('11/11 21:00', 'sacar la basura')),
            ('pasado mañana a la tarde merienda', ('13/11 16:00', 'merienda')),
        ], at(15))

    def test_only_a_part_of_the_day(self):
        self.check([
            ('esta noche sacar la basura', ('11/11 21:00', 'sacar la basura')),
            ('sacar la basura esta noche', ('11/11 21:00', 'sacar la basura')),
            ('esta tarde llamar al plomero', ('11/11 16:00', 'llamar al plomero')),
            ('a la noche sacar la basura', ('11/11 21:00', 'sacar la basura')),
            ('a la tarde llamar al plomero', ('11/11 16:00', 'llamar al plomero')),
            # Noon already passed today
            ('al mediodía almorzar', ('12/11 12:00', 'almorzar')),
            ('a la mañana ir al banco', ('12/11 09:00', 'ir al banco')),
            ('a medianoche brindar', ('12/11 00:00', 'brindar')),
        ], at(15))

    def test_esta_keeps_today_even_if_it_passed(self):
        # The caller answers that the date must be in the future
        self.check([
            ('esta tarde llamar al plomero', ('11/11 16:00', 'llamar al plomero')),
            ('esta mañana ir al banco', ('11/11 09:00', 'ir al banco')),
        ], at(18))

    def test_explicit_date_with_a_part_of_the_day(self):
        self.check([
            ('el 20 a la tarde pagar alquiler', ('20/11 16:00', 'pagar alquiler')),
            ('20/12 a la noche cena', ('20/12 21:00', 'cena')),
            ('el 25 de diciembre al mediodía almuerzo', ('25/12 12:00', 'almuerzo')),
        ], at(15))

    def test_la_noche_inside_the_reminder_is_not_a_time(self):
        self.check([
            ('mañana comprar pastillas para la noche', ('12/11 09:00', 'comprar pastillas para la noche')),
            ('mañana comprar para esta noche', ('12/11 09:00', 'comprar para esta noche')),
            ('el 20 comprar para esta noche', ('20/11 09:00', 'comprar para esta noche')),
        ], at(15))

    def test_esta_noche_is_not_the_time_of_another_day(self):
        self.check([
            ('el 20 comprar velas esta noche', ('20/11 09:00', 'comprar velas esta noche')),
            ('el viernes llevar lo de esta tarde', ('13/11 09:00', 'llevar lo esta tarde')),
            ('en 3 días devolver lo de esta noche', ('14/11 15:00', 'devolver lo esta noche')),
            ('hoy sacar la basura esta noche', ('11/11 21:00', 'sacar la basura')),
        ], at(15))


class HourWithHintAndNoALas(ParsingCases):
    def test_hour_plus_part_of_the_day_next_to_the_day(self):
        self.check([
            ('mañana 9 de la noche tomar pastilla', ('12/11 21:00', 'tomar pastilla')),
            ('mañana 9 pm gimnasio', ('12/11 21:00', 'gimnasio')),
            ('el viernes 9 de la noche cine', ('13/11 21:00', 'cine')),
            ('20/12 9 de la mañana viaje', ('20/12 09:00', 'viaje')),
        ], at(15))


class Deadlines(ParsingCases):
    def test_antes_de_las_reminds_an_hour_before(self):
        self.check([
            ('antes de las 5 entregar informe', ('11/11 16:00', 'entregar informe')),
            ('antes de las 17 entregar informe', ('11/11 16:00', 'entregar informe')),
            ('antes de las 17:30 entregar informe', ('11/11 16:30', 'entregar informe')),
            ('mañana antes de las 9 llamar', ('12/11 08:00', 'llamar')),
            ('el viernes antes de las 18 entregar informe', ('13/11 17:00', 'entregar informe')),
            ('el 20/12 antes de las 10 pagar', ('20/12 09:00', 'pagar')),
            ('antes de las 9 de la noche llamar', ('11/11 20:00', 'llamar')),
        ], at(15))

    def test_with_less_than_an_hour_left_it_reminds_halfway(self):
        self.check([
            ('antes de las 17 entregar informe', ('11/11 16:45', 'entregar informe')),
        ], at(16, 30))


class DayTheMonthDoesNotHave(ParsingCases):
    def test_it_becomes_the_last_day_of_the_month(self):
        self.check([
            ('el 31 pagar alquiler', ('30/11/2026 09:00', 'pagar alquiler')),
            ('el 31 a las 10 pagar alquiler', ('30/11/2026 10:00', 'pagar alquiler')),
            ('el 30 pagar alquiler', ('30/11/2026 09:00', 'pagar alquiler')),
            ('el 20 pagar alquiler', ('20/11/2026 09:00', 'pagar alquiler')),
            # The 5th already passed: next month
            ('el 5 pagar alquiler', ('05/12/2026 09:00', 'pagar alquiler')),
        ], at(15), WITH_YEAR)

    def test_last_day_already_passed_goes_to_next_month(self):
        november_30_evening = TZ.localize(datetime(2026, 11, 30, 20, 0))
        self.check([
            ('el 31 pagar alquiler', ('31/12/2026 09:00', 'pagar alquiler')),
        ], november_30_evening, WITH_YEAR)

    def test_february(self):
        january_31_evening = TZ.localize(datetime(2027, 1, 31, 20, 0))
        self.check([
            ('el 31 pagar alquiler', ('28/02/2027 09:00', 'pagar alquiler')),
            ('el 30 pagar alquiler', ('28/02/2027 09:00', 'pagar alquiler')),
        ], january_31_evening, WITH_YEAR)


class MonthNameWithoutText(ParsingCases):
    def test_does_not_crash(self):
        self.check([
            ('25 de diciembre', ('25/12/2026 09:00', '')),
        ], at(15), WITH_YEAR)


if __name__ == '__main__':
    unittest.main()
