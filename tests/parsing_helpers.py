"""Shared helpers for the date/time parsing tests."""
import os
import sys
import unittest
from datetime import datetime

import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers import extract_date_and_text  # noqa: E402

TZ = pytz.timezone('America/Argentina/Buenos_Aires')


def at(hour, minute=0, day=11):
    """A fixed 'now' on Wednesday 11/11/2026 (or another day of that month)."""
    return TZ.localize(datetime(2026, 11, day, hour, minute))


def parse(text, now, date_format='%d/%m %H:%M'):
    """Return (formatted date, reminder_text) for a message read at `now`."""
    parsed, reminder_text = extract_date_and_text(text, now=now)
    return (parsed.strftime(date_format) if parsed else None, reminder_text)


class ParsingCases(unittest.TestCase):
    """Base class: check a list of (message, (expected date, expected text)) pairs."""

    def check(self, cases, now, date_format='%d/%m %H:%M'):
        for text, expected in cases:
            with self.subTest(text=text, now=now.strftime('%a %H:%M')):
                self.assertEqual(parse(text, now, date_format), expected)
