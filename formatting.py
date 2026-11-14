"""Telegram messages in HTML that any text the user writes cannot break (issue #9).

Text the user wrote goes through escape() or highlight(); our own formatting uses HTML
tags that open and close on the same line. reply_html() splits long messages so none
goes over Telegram's limit.
"""
import html
import re
from typing import List

# Telegram allows 4096 characters per message; the margin covers emoji, which Telegram
# counts as two
MAX_MESSAGE_LENGTH = 4000

# Where a long message is split, from the most to the least natural place
SEPARATORS = ['\n\n', '\n', ' ']


def escape(text) -> str:
    """User text, safe inside an HTML message."""
    return html.escape(str(text), quote=False)


def highlight(text: str, keyword: str) -> str:
    """Escaped text with every match of keyword (any case) in bold."""
    if not keyword:
        return escape(text)
    parts = re.split(f'({re.escape(keyword)})', text, flags=re.IGNORECASE)
    return ''.join(f'<b>{escape(part)}</b>' if index % 2 else escape(part)
                   for index, part in enumerate(parts))


def from_markdown(template: str) -> str:
    """Convert a fixed text of ours with **bold** and `code` to HTML.

    Only for texts written in the code: user text must go through escape().
    """
    converted = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escape(template))
    return re.sub(r'`([^`]+)`', r'<code>\1</code>', converted)


def _hard_cut(text: str, limit: int) -> List[str]:
    """Cut a text with no separator left, never inside an HTML entity such as &amp;."""
    pieces = []
    while len(text) > limit:
        cut = limit
        entity_start = text.rfind('&', max(0, cut - 8), cut)
        if entity_start != -1 and ';' not in text[entity_start:cut]:
            cut = entity_start
        pieces.append(text[:cut])
        text = text[cut:]
    pieces.append(text)
    return pieces


def split_message(text: str, limit: int = MAX_MESSAGE_LENGTH, separators: List[str] = None) -> List[str]:
    """Split into parts of at most limit characters: between blocks, then lines, then words."""
    separators = SEPARATORS if separators is None else separators
    if len(text) <= limit:
        return [text] if text.strip() else []
    if not separators:
        return _hard_cut(text, limit)

    separator, finer = separators[0], separators[1:]
    parts = []
    current = ''
    for block in text.split(separator):
        candidate = f'{current}{separator}{block}' if current else block
        if len(candidate) <= limit:
            current = candidate
            continue
        if current.strip():
            parts.append(current)
        if len(block) <= limit:
            current = block
        else:
            parts.extend(split_message(block, limit, finer))
            current = ''
    if current.strip():
        parts.append(current)
    return [part.strip('\n') for part in parts]


async def reply_html(message, text: str):
    """Reply in HTML, in as many messages as needed."""
    for part in split_message(text):
        await message.reply_text(part, parse_mode='HTML')
