"""Who can use the admin and special ("novia") modes.

Both are configured with environment variables (Fly secrets in production), never in the
repository:
- ADMIN_USER_IDS: comma separated Telegram user ids. There is no admin password to guess
  or leak, and removing an id revokes the access.
- GIRLFRIEND_PHRASE: the answer to the /novia question. A right answer sends the admins a
  request to approve; without the phrase or without admins the mode cannot be requested.
"""
import logging
import os
import re
import time
import unicodedata
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

ADMIN_USER_IDS_VARIABLE = 'ADMIN_USER_IDS'
GIRLFRIEND_PHRASE_VARIABLE = 'GIRLFRIEND_PHRASE'

# An answer may add a few words to the phrase ("jaja", "te amo"), but not so many that
# sending a long list of words would contain it by chance
MAX_EXTRA_WORDS = 3

# Wrong answers allowed per user before /novia stops asking for a while
MAX_FAILED_ATTEMPTS = 5
FAILED_ATTEMPTS_WINDOW_SECONDS = 60 * 60

# Kept in memory: a restart clears it, which only gives a few more attempts
_failed_attempts: Dict[int, List[float]] = {}


def admin_user_ids() -> Set[int]:
    """Telegram user ids listed in ADMIN_USER_IDS; invalid entries are ignored."""
    ids = set()
    for value in os.getenv(ADMIN_USER_IDS_VARIABLE, '').split(','):
        value = value.strip()
        if not value:
            continue
        try:
            ids.add(int(value))
        except ValueError:
            logger.error(f"Ignoring invalid user id in {ADMIN_USER_IDS_VARIABLE}: {value!r}")
    return ids


def is_admin(user) -> bool:
    """Whether a Telegram user (update.effective_user, which can be None) is an admin."""
    return user is not None and user.id in admin_user_ids()


def _words(text: str) -> List[str]:
    """Lowercase words without accents or punctuation."""
    decomposed = unicodedata.normalize('NFD', text.lower())
    without_accents = ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')
    return re.findall(r'\w+', without_accents)


def _girlfriend_phrase_words() -> Set[str]:
    return set(_words(os.getenv(GIRLFRIEND_PHRASE_VARIABLE, '')))


def girlfriend_mode_available() -> bool:
    """The special mode needs GIRLFRIEND_PHRASE, and an admin to approve the requests."""
    return bool(_girlfriend_phrase_words()) and bool(admin_user_ids())


def is_girlfriend_answer(text: Optional[str]) -> bool:
    """The answer has every word of the phrase, in any order, plus at most a few more.

    Case, accents and punctuation do not matter.
    """
    expected = _girlfriend_phrase_words()
    answer = set(_words(text or ''))
    return bool(expected) and expected <= answer and len(answer - expected) <= MAX_EXTRA_WORDS


def _recent_failures(user_id: int, now: float) -> List[float]:
    recent = [moment for moment in _failed_attempts.get(user_id, [])
              if now - moment < FAILED_ATTEMPTS_WINDOW_SECONDS]
    if recent:
        _failed_attempts[user_id] = recent
    else:
        _failed_attempts.pop(user_id, None)
    return recent


def is_locked_out(user_id: int, now: Optional[float] = None) -> bool:
    """Too many wrong answers in the last hour."""
    now = time.monotonic() if now is None else now
    return len(_recent_failures(user_id, now)) >= MAX_FAILED_ATTEMPTS


def record_failed_attempt(user_id: int, now: Optional[float] = None) -> None:
    now = time.monotonic() if now is None else now
    _failed_attempts[user_id] = _recent_failures(user_id, now) + [now]


def clear_failed_attempts(user_id: int) -> None:
    _failed_attempts.pop(user_id, None)
