"""The text that is saved for a reminder (issue #5).

Run from the project root:
    python3 -m unittest discover -s tests -v

'now' is Wednesday 11/11/2026 at 15:00.
"""
import unittest

from parsing_helpers import ParsingCases, at


class WordsOfTheReminderAreKept(ParsingCases):
    def test_de_and_que_inside_the_reminder(self):
        self.check([
            ('mañana comprar regalo de cumpleaños de mamá', ('12/11 09:00', 'comprar regalo de cumpleaños de mamá')),
            ('mañana 10:00 decirle a Juan que venga', ('12/11 10:00', 'decirle a Juan que venga')),
            ('en 2 meses renovar el pasaporte de la nena', ('11/01 15:00', 'renovar el pasaporte de la nena')),
            ('hoy a las 20 cenar', ('11/11 20:00', 'cenar')),
        ], at(15))

    def test_words_that_look_like_the_order_but_are_content(self):
        self.check([
            ('mañana acordar precio con el cliente', ('12/11 09:00', 'acordar precio con el cliente')),
            ('mañana pagar el aviso de vencimiento', ('12/11 09:00', 'pagar el aviso de vencimiento')),
            ('el viernes a las 10 recordar a Juan que traiga el libro', ('13/11 10:00', 'recordar a Juan que traiga el libro')),
        ], at(15))


class TheOrderIsRemoved(ParsingCases):
    def test_order_opening_the_message(self):
        self.check([
            ('recordame mañana a las 10 ir al médico', ('12/11 10:00', 'ir al médico')),
            ('Recordame que mañana tengo turno', ('12/11 09:00', 'tengo turno')),
            ('recordame de comprar pan mañana', ('12/11 09:00', 'comprar pan')),
            ('recordar mañana 10:00 dentista', ('12/11 10:00', 'dentista')),
            ('aviso mañana a las 10 reunión', ('12/11 10:00', 'reunión')),
            ('avisame en 2 horas que saque la ropa', ('11/11 17:00', 'saque la ropa')),
            ('haceme acordar el viernes comprar cerveza', ('13/11 09:00', 'comprar cerveza')),
            ('acordarme de llamar a mamá mañana', ('12/11 09:00', 'llamar a mamá')),
            ('/recordar mañana 18:00 comprar comida', ('12/11 18:00', 'comprar comida')),
        ], at(15))

    def test_order_after_the_date(self):
        self.check([
            ('Mañana a las 14 recordame que tengo turno médico', ('12/11 14:00', 'tengo turno médico')),
            ('El viernes a las 18hs haceme acordar de comprar cerveza', ('13/11 18:00', 'comprar cerveza')),
            ('Mañana a las 10 acordarme de la cita', ('12/11 10:00', 'la cita')),
            ('el lunes avísame que venza el plazo', ('16/11 09:00', 'venza el plazo')),
        ], at(15))


class NothingOfTheDateIsLeft(ParsingCases):
    def test_dangling_words_before_a_date_at_the_end(self):
        self.check([
            ('comprar pan para mañana', ('12/11 09:00', 'comprar pan')),
            ('comprar pan para el viernes', ('13/11 09:00', 'comprar pan')),
            ('pagar la cuota del 20/12', ('20/12 09:00', 'pagar la cuota')),
            ('confirmar el turno de mañana a las 9', ('12/11 09:00', 'confirmar el turno')),
            ('llamar a Juan el viernes a las 10', ('13/11 10:00', 'llamar a Juan')),
        ], at(15))

    def test_dangling_words_in_the_middle(self):
        self.check([
            ('a las 10 de la mañana de mañana llamar', ('12/11 10:00', 'llamar')),
            ('reunión a las 10 de mañana con Juan', ('12/11 10:00', 'reunión con Juan')),
            ('confirmar el turno de mañana a las 9 con el médico', ('12/11 09:00', 'confirmar el turno con el médico')),
            ('comprar regalo para el viernes a las 10 y envolverlo', ('13/11 10:00', 'comprar regalo y envolverlo')),
        ], at(15))

    def test_loose_punctuation(self):
        self.check([
            ('mañana a las 10: ir al médico', ('12/11 10:00', 'ir al médico')),
            ('mañana, comprar pan', ('12/11 09:00', 'comprar pan')),
            ('recordame, mañana a las 10 ir al médico', ('12/11 10:00', 'ir al médico')),
            ('mañana de 10 a 12 curso', ('12/11 09:00', 'de 10 a 12 curso')),
        ], at(15))


class NumbersInTheReminderAreNotDates(ParsingCases):
    def test_a_day_named_first_wins_over_el_n(self):
        self.check([
            ('el lunes comprar el 2 por 1 de helado', ('16/11 09:00', 'comprar el 2 por 1 de helado')),
            ('el lunes llevar el 5 al taller', ('16/11 09:00', 'llevar el 5 al taller')),
            ('mañana a las 10 tomar el 60 hasta el centro', ('12/11 10:00', 'tomar el 60 hasta el centro')),
        ], at(15))

    def test_el_n_that_is_not_a_day_of_the_month(self):
        self.check([
            ('comprar el 2 por 1 a las 18', ('11/11 18:00', 'comprar el 2 por 1')),
            ('a las 18 aprovechar el 3x2 del super', ('11/11 18:00', 'aprovechar el 3x2 del super')),
            ('a las 21 ver el 5 de copas', ('11/11 21:00', 'ver el 5 de copas')),
        ], at(15))

    def test_el_n_after_the_message_already_said_when(self):
        self.check([
            ('a las 21 ver el 13', ('11/11 21:00', 'ver el 13')),
            ('esta noche ver el 13', ('11/11 21:00', 'ver el 13')),
            ('a la noche tomar el 60 a casa', ('11/11 21:00', 'tomar el 60 a casa')),
            ('en 2 horas ver el 9', ('11/11 17:00', 'ver el 9')),
            # The hour right before the day belongs to it
            ('a las 10 el 20 pagar', ('20/11 10:00', 'pagar')),
        ], at(15))

    def test_el_n_is_still_a_date(self):
        self.check([
            ('el 20 pagar alquiler', ('20/11 09:00', 'pagar alquiler')),
            ('pagar alquiler el 20', ('20/11 09:00', 'pagar alquiler')),
            ('el 20 comprar algo para mañana', ('20/11 09:00', 'comprar algo para mañana')),
            ('el 20 de este mes pagar', ('20/11 09:00', 'pagar')),
        ], at(15))


class DateWithNoText(ParsingCases):
    def test_the_text_is_empty_so_the_bot_asks_for_it(self):
        self.check([
            ('mañana a las 10', ('12/11 10:00', '')),
            ('mañana', ('12/11 09:00', '')),
            ('mañana 18:00', ('12/11 18:00', '')),
            ('el viernes', ('13/11 09:00', '')),
            ('esta noche', ('11/11 21:00', '')),
            ('en 10 minutos', ('11/11 15:10', '')),
            ('recordame mañana a las 10', ('12/11 10:00', '')),
            ('20/12/2026 09:30', ('20/12 09:30', '')),
        ], at(15))


if __name__ == '__main__':
    unittest.main()
