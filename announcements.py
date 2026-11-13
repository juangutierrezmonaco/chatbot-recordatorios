"""Tell users what changed after a deploy.

The notes live in release_notes.json, newest release first. On startup the bot sends the
releases it has not announced yet to every chat that uses it, and records the newest one
so a plain restart does not send them again.
"""
import asyncio
import html
import json
import logging
import os
import re
from typing import Dict, List, Optional

from telegram import Bot

import db

logger = logging.getLogger(__name__)

RELEASE_NOTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'release_notes.json')
LAST_ANNOUNCED_KEY = 'last_announced_release'

# Telegram allows 4096 characters per message; keep a margin for the header
MAX_MESSAGE_LENGTH = 3800

# Pause between chats so a larger user base stays under Telegram's rate limits
SECONDS_BETWEEN_CHATS = 0.05

MESSAGE_HEADER = "🆕 <b>Novedades del bot</b>"


def load_releases(path: str = RELEASE_NOTES_PATH) -> List[Dict]:
    """Releases from the notes file, newest first. An unreadable file means no releases."""
    try:
        with open(path, encoding='utf-8') as notes_file:
            releases = json.load(notes_file)['releases']
    except (OSError, ValueError, KeyError, TypeError) as error:
        logger.error(f"Could not read release notes from {path}: {error}")
        return []

    valid_releases = []
    for release in releases:
        if _is_valid_release(release):
            valid_releases.append(release)
        else:
            logger.error(f"Skipping malformed release in {path}: {release!r}")

    return valid_releases


def _is_valid_release(release) -> bool:
    """A release needs a version and a non-empty list of non-empty text notes."""
    if not isinstance(release, dict) or not isinstance(release.get('version'), str) or not release['version']:
        return False

    notes = release.get('notes')
    return (
        isinstance(notes, list)
        and bool(notes)
        and all(isinstance(note, str) and note.strip() for note in notes)
    )


def pending_releases(releases: List[Dict], last_announced: Optional[str]) -> List[Dict]:
    """Releases newer than the last announced one, oldest first.

    With nothing announced yet, or a last version that is no longer in the file, only the
    newest release is pending: users are not sent the whole history.
    """
    if not releases:
        return []

    versions = [release['version'] for release in releases]
    if last_announced not in versions:
        return [releases[0]]

    return list(reversed(releases[:versions.index(last_announced)]))


def _note_to_html(note: str) -> str:
    """Escape a note for Telegram HTML; `backticks` become code (commands, examples)."""
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', html.escape(note))


def format_release_messages(releases: List[Dict]) -> List[str]:
    """Telegram messages (HTML) listing the notes of the given releases.

    Usually one message; split by note if the notes do not fit in one.
    """
    lines = [f"• {_note_to_html(note)}" for release in releases for note in release['notes']]

    messages = []
    current = MESSAGE_HEADER + "\n"
    for line in lines:
        if len(current) + len(line) + 2 > MAX_MESSAGE_LENGTH:
            messages.append(current.rstrip())
            current = ""
        current += "\n" + line

    messages.append(current.rstrip())
    return messages


async def announce_new_releases(bot: Bot, releases: Optional[List[Dict]] = None) -> int:
    """Send the releases not announced yet to every chat that uses the bot.

    Returns the number of chats that received them. A chat that cannot be reached (it
    blocked the bot, for example) is skipped; the release still counts as announced.
    If no chat could be reached (Telegram down at startup), nothing is recorded and the
    next start tries again.
    """
    if releases is None:
        releases = load_releases()

    to_announce = pending_releases(releases, db.get_app_state(LAST_ANNOUNCED_KEY))
    if not to_announce:
        return 0

    messages = format_release_messages(to_announce)
    chat_ids = db.get_engaged_chat_ids()

    delivered = 0
    for chat_id in chat_ids:
        try:
            for message in messages:
                await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            delivered += 1
        except Exception as error:
            logger.warning(f"Could not send release notes to chat {chat_id}: {error}")
        await asyncio.sleep(SECONDS_BETWEEN_CHATS)

    newest = to_announce[-1]['version']
    if chat_ids and not delivered:
        logger.error(f"Release {newest} could not be sent to any chat; it will be retried on the next start")
        return 0

    db.set_app_state(LAST_ANNOUNCED_KEY, newest)
    logger.info(f"Release {newest} announced to {delivered}/{len(chat_ids)} chats")
    return delivered


async def announce_on_startup(application) -> None:
    """post_init hook for the Telegram application: announce, never block the startup."""
    try:
        await announce_new_releases(application.bot)
    except Exception as error:
        logger.error(f"Release announcement failed: {error}")
