import re
import logging
from datetime import datetime, timedelta
import pytz
import dateparser
from telegram import Update
from telegram.ext import ContextTypes
import db
import scheduler

logger = logging.getLogger(__name__)

# Configure dateparser for Spanish
DATEPARSER_SETTINGS = {
    'PREFER_DATES_FROM': 'future',
    'TIMEZONE': 'America/Argentina/Buenos_Aires',
    'DATE_ORDER': 'DMY',
    'DEFAULT_LANGUAGES': ['es']
}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    message = """
🤖 ¡Hola! Soy tu bot de recordatorios personal.

📝 **Cómo usarme:**

**Comandos:**
/recordar <fecha/hora> <texto> - Crear recordatorio
/lista - Ver recordatorios activos
/hoy - Ver recordatorios de hoy
/buscar <palabra> - Buscar recordatorios
/historial - Ver recordatorios pasados
/cancelar <id> - Cancelar recordatorio

**Ejemplos de comandos:**
• `/recordar mañana 18:00 comprar comida`
• `/recordar en 30m apagar el horno`
• `/recordar 2025-09-20 09:30 reunión con Juan`

**Lenguaje natural:**
También puedes escribir directamente:
• "Mañana a las 2 recordame que tengo turno médico"
• "En 45 minutos recordame sacar la pizza"
• "El viernes a las 18hs haceme acordar de comprar cerveza"

¡Empezá a crear tus recordatorios! 🎯
    """

    await update.message.reply_text(message)

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /recordar command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /recordar <fecha/hora> <texto>\n"
            "Ejemplo: /recordar mañana 18:00 comprar comida"
        )
        return

    full_text = ' '.join(context.args)
    result = await process_reminder(update, context, full_text)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /lista command."""
    chat_id = update.effective_chat.id
    reminders = db.get_active_reminders(chat_id)

    if not reminders:
        await update.message.reply_text("📝 No tienes recordatorios activos.")
        return

    message = "📋 **Tus recordatorios activos:**\n\n"

    for reminder in reminders:
        formatted_date = reminder['datetime'].strftime("%d/%m/%Y %H:%M")
        message += f"🔔 **#{reminder['id']}** - {formatted_date}\n"
        message += f"   {reminder['text']}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /hoy command."""
    chat_id = update.effective_chat.id
    reminders = db.get_today_reminders(chat_id)

    if not reminders:
        await update.message.reply_text("📅 No tienes recordatorios para hoy.")
        return

    message = "📅 **Tus recordatorios para hoy:**\n\n"

    for reminder in reminders:
        # Show only time for today's reminders (not date)
        formatted_time = reminder['datetime'].strftime("%H:%M")
        message += f"🔔 **#{reminder['id']}** - {formatted_time}\n"
        message += f"   {reminder['text']}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /buscar command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /buscar <palabra o frase>\n"
            "Ejemplos:\n"
            "• /buscar comida\n"
            "• /buscar \"reunión trabajo\""
        )
        return

    chat_id = update.effective_chat.id
    keyword = ' '.join(context.args)

    # Remove quotes if present
    if (keyword.startswith('"') and keyword.endswith('"')) or (keyword.startswith("'") and keyword.endswith("'")):
        keyword = keyword[1:-1]

    if not keyword.strip():
        await update.message.reply_text("❌ La búsqueda no puede estar vacía.")
        return

    reminders = db.search_reminders(chat_id, keyword)

    if not reminders:
        await update.message.reply_text(f"🔍 No se encontraron recordatorios con: \"{keyword}\"")
        return

    message = f"🔍 **Recordatorios encontrados con \"{keyword}\":**\n\n"

    for reminder in reminders:
        formatted_date = reminder['datetime'].strftime("%d/%m/%Y %H:%M")

        # Highlight the keyword in the text (simple bold formatting)
        highlighted_text = _highlight_keyword(reminder['text'], keyword)

        message += f"🔔 **#{reminder['id']}** - {formatted_date}\n"
        message += f"   {highlighted_text}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /historial command."""
    chat_id = update.effective_chat.id

    # Parse filter argument
    status_filter = None
    if context.args:
        filter_arg = context.args[0].lower()
        if filter_arg in ['enviados', 'sent']:
            status_filter = 'sent'
        elif filter_arg in ['cancelados', 'cancelled']:
            status_filter = 'cancelled'
        elif filter_arg not in ['todos', 'all']:
            await update.message.reply_text(
                "❌ Filtro inválido. Usa:\n"
                "• /historial\n"
                "• /historial enviados\n"
                "• /historial cancelados"
            )
            return

    reminders = db.get_historical_reminders(chat_id, status_filter)

    if not reminders:
        if status_filter == 'sent':
            message = "📜 No tienes recordatorios enviados."
        elif status_filter == 'cancelled':
            message = "📜 No tienes recordatorios cancelados."
        else:
            message = "📜 No tienes historial de recordatorios."

        await update.message.reply_text(message)
        return

    # Build header message
    if status_filter == 'sent':
        header = "📜 **Recordatorios enviados:**"
    elif status_filter == 'cancelled':
        header = "📜 **Recordatorios cancelados:**"
    else:
        header = "📜 **Historial de recordatorios:**"

    message = f"{header}\n\n"

    for reminder in reminders:
        formatted_date = reminder['datetime'].strftime("%d/%m/%Y %H:%M")

        # Status emoji and text
        if reminder['status'] == 'sent':
            status_emoji = "✅"
            status_text = "Enviado"
        elif reminder['status'] == 'cancelled':
            status_emoji = "❌"
            status_text = "Cancelado"
        else:
            status_emoji = "❓"
            status_text = reminder['status']

        message += f"{status_emoji} **#{reminder['id']}** - {formatted_date} ({status_text})\n"
        message += f"   {reminder['text']}\n\n"

    message += f"_(Mostrando últimos {len(reminders)} recordatorios)_"
    await update.message.reply_text(message, parse_mode='Markdown')

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /cancelar command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /cancelar <id(s)>\n"
            "Ejemplos:\n"
            "• /cancelar 3\n"
            "• /cancelar 1,2,3\n"
            "• /cancelar 1-5\n"
            "• /cancelar 1 2 3\n"
            "• /cancelar todos"
        )
        return

    chat_id = update.effective_chat.id
    full_text = ' '.join(context.args)

    # Handle "todos" case
    if full_text.lower() in ['todos', 'all']:
        # Get all active reminder IDs before cancelling
        active_reminders = db.get_active_reminders(chat_id)
        reminder_ids = [r['id'] for r in active_reminders]

        if reminder_ids:
            cancelled_count = db.cancel_all_reminders(chat_id)
            scheduler.cancel_multiple_reminder_jobs(reminder_ids)
            await update.message.reply_text(f"❌ Se cancelaron {cancelled_count} recordatorios")
        else:
            await update.message.reply_text("📝 No tienes recordatorios activos para cancelar")
        return

    # Parse reminder IDs from various formats
    reminder_ids = _parse_reminder_ids(full_text)

    if not reminder_ids:
        await update.message.reply_text("❌ Formato inválido. Usa números separados por comas, espacios o rangos (ej: 1-5)")
        return

    # Cancel multiple reminders
    if len(reminder_ids) == 1:
        # Single reminder - use original logic for backward compatibility
        reminder_id = reminder_ids[0]
        if db.cancel_reminder(chat_id, reminder_id):
            scheduler.cancel_reminder_job(reminder_id)
            await update.message.reply_text(f"❌ Recordatorio #{reminder_id} cancelado")
        else:
            await update.message.reply_text(f"❌ No se encontró el recordatorio #{reminder_id}")
    else:
        # Multiple reminders
        db_result = db.cancel_multiple_reminders(chat_id, reminder_ids)
        scheduler.cancel_multiple_reminder_jobs(db_result["cancelled"])

        # Build response message
        message_parts = []
        if db_result["cancelled"]:
            cancelled_str = ", ".join(f"#{id}" for id in db_result["cancelled"])
            message_parts.append(f"❌ Cancelados: {cancelled_str}")

        if db_result["not_found"]:
            not_found_str = ", ".join(f"#{id}" for id in db_result["not_found"])
            message_parts.append(f"❓ No encontrados: {not_found_str}")

        if not message_parts:
            message_parts.append("❌ No se pudieron cancelar los recordatorios")

        await update.message.reply_text("\n".join(message_parts))

async def free_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle natural language messages."""
    text = update.message.text.lower()

    # Check if it's a reminder attempt
    keywords = ['recordar', 'recordame', 'aviso', 'avisame', 'haceme acordar', 'acordar']

    if any(keyword in text for keyword in keywords):
        await process_reminder(update, context, update.message.text)
    else:
        await update.message.reply_text(
            "🤔 No entiendo. Usa /start para ver cómo crear recordatorios."
        )

async def process_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Process a reminder from command or natural language."""
    chat_id = update.effective_chat.id

    # Extract date/time and text
    datetime_obj, reminder_text = extract_date_and_text(text)

    if not datetime_obj:
        await update.message.reply_text(
            "❌ No pude entender la fecha/hora. Ejemplos:\n"
            "• mañana 18:00\n"
            "• en 30 minutos\n"
            "• 20/09/2025 09:30"
        )
        return

    if not reminder_text:
        await update.message.reply_text("❌ Falta el texto del recordatorio.")
        return

    # Verify that the date is in the future
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
    if datetime_obj <= now:
        await update.message.reply_text("❌ La fecha debe ser en el futuro.")
        return

    # Save to DB and schedule
    reminder_id = db.add_reminder(chat_id, reminder_text, datetime_obj)
    scheduler.schedule_reminder(
        context.bot, chat_id, reminder_id, reminder_text, datetime_obj
    )

    # Confirm to user
    formatted_date = datetime_obj.strftime("%d/%m/%Y %H:%M")
    await update.message.reply_text(
        f"✅ Dale, te aviso el {formatted_date}: \"{reminder_text}\" (ID #{reminder_id})"
    )

def _smart_day_parse(day: int, now: datetime) -> datetime:
    """Parse a day of the month intelligently (e.g., 'el 20')."""
    if day < 1 or day > 31:
        return None

    # Try current month first
    try:
        target_date = now.replace(day=day, hour=9, minute=0, second=0, microsecond=0)
        # If the date is in the past, try next month
        if target_date <= now:
            if now.month == 12:
                target_date = target_date.replace(year=now.year + 1, month=1)
            else:
                target_date = target_date.replace(month=now.month + 1)
        return target_date
    except ValueError:
        # Day doesn't exist in current month, try next month
        try:
            if now.month == 12:
                target_date = now.replace(year=now.year + 1, month=1, day=day, hour=9, minute=0, second=0, microsecond=0)
            else:
                target_date = now.replace(month=now.month + 1, day=day, hour=9, minute=0, second=0, microsecond=0)
            return target_date
        except ValueError:
            return None

def _smart_date_parse(day: int, month: int, now: datetime) -> datetime:
    """Parse day/month intelligently (e.g., '20/12')."""
    if day < 1 or day > 31 or month < 1 or month > 12:
        return None

    # Try current year first
    try:
        target_date = now.replace(year=now.year, month=month, day=day, hour=9, minute=0, second=0, microsecond=0)
        # If the date is in the past, use next year
        if target_date <= now:
            target_date = target_date.replace(year=now.year + 1)
        return target_date
    except ValueError:
        return None

def _smart_hour_parse(hour: int, minute: int, now: datetime) -> datetime:
    """Parse hour intelligently (e.g., 'a las 9')."""
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None

    # If hour is already in 24h format (13-23), use as is
    if hour >= 13:
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_time <= now:
            target_time += timedelta(days=1)
        return target_time

    # For hours 1-12, we need to infer AM/PM
    # Create both AM and PM options
    am_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    pm_time = now.replace(hour=hour + 12, minute=minute, second=0, microsecond=0)

    # Smart inference logic:
    # 1. If it's before 6 AM, prefer AM times
    if now.hour < 6:
        if am_time > now:
            return am_time
        elif pm_time > now:
            return pm_time
        else:
            return am_time + timedelta(days=1)

    # 2. If it's morning (6 AM - 11:59 AM), prefer the next available time
    elif 6 <= now.hour < 12:
        if am_time > now:
            return am_time
        elif pm_time > now:
            return pm_time
        else:
            return am_time + timedelta(days=1)

    # 3. If it's afternoon/evening (12 PM onwards), prefer PM for reasonable hours
    else:
        # For typical evening hours (6-11), strongly prefer PM if it's future
        if 6 <= hour <= 11 and pm_time > now:
            return pm_time
        # For early hours (1-5), could be either but prefer the next available
        elif 1 <= hour <= 5:
            if pm_time > now:
                return pm_time
            else:
                return am_time + timedelta(days=1)
        # For hours like 12, prefer PM if available
        elif hour == 12:
            if pm_time > now:
                return pm_time
            else:
                return am_time + timedelta(days=1)
        # For other cases, use next available
        else:
            if am_time > now:
                return am_time
            elif pm_time > now:
                return pm_time
            else:
                return am_time + timedelta(days=1)

def _parse_reminder_ids(text: str) -> list:
    """Parse reminder IDs from various formats."""
    reminder_ids = []

    # Remove extra whitespace
    text = text.strip()

    # Handle comma-separated: "1,2,3"
    if ',' in text:
        parts = text.split(',')
        for part in parts:
            part = part.strip()
            if part.isdigit():
                reminder_ids.append(int(part))
        return reminder_ids

    # Handle ranges: "1-5"
    if '-' in text and len(text.split()) == 1:
        try:
            start, end = text.split('-')
            start, end = int(start.strip()), int(end.strip())
            if start <= end:
                reminder_ids.extend(range(start, end + 1))
                return reminder_ids
        except ValueError:
            pass

    # Handle space-separated: "1 2 3"
    parts = text.split()
    for part in parts:
        if part.isdigit():
            reminder_ids.append(int(part))

    return reminder_ids

def _highlight_keyword(text: str, keyword: str) -> str:
    """Highlight keyword in text using markdown bold formatting."""
    # Case-insensitive replacement
    import re
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)

    def replace_func(match):
        return f"**{match.group()}**"

    # Only highlight if the keyword isn't already part of markdown formatting
    # Simple approach: avoid double-formatting
    if "**" in text:
        # If text already has markdown, don't highlight to avoid conflicts
        return text

    return pattern.sub(replace_func, text)

def extract_date_and_text(text: str):
    """Extract date/time and reminder text."""

    # Clean text
    text = text.strip()

    # Remove command words if they exist
    text = re.sub(r'^\/(?:recordar)\s*', '', text, flags=re.IGNORECASE)

    # Remove request words
    request_words = [
        'recordame', 'recordar', 'avisame', 'aviso', 'haceme acordar',
        'acordar', 'que', 'de que', 'de'
    ]

    for word in request_words:
        text = re.sub(rf'\b{word}\b', '', text, flags=re.IGNORECASE)

    text = re.sub(r'\s+', ' ', text).strip()

    # Get current time for smart inference
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

    # Smart patterns for intuitive date parsing
    smart_patterns = [
        # "el 20" (day of current month/year)
        (r'\bel\s+(\d{1,2})\b(?![\/\-:])', lambda m: _smart_day_parse(int(m.group(1)), now)),
        # "el 20/12" or "20/12" (day/month of current year)
        (r'\b(?:el\s+)?(\d{1,2})[\/\-](\d{1,2})\b(?![\-:])', lambda m: _smart_date_parse(int(m.group(1)), int(m.group(2)), now)),
        # "a las 9" (smart hour inference)
        (r'\ba\s*las?\s+(\d{1,2})(?::(\d{2}))?\b', lambda m: _smart_hour_parse(int(m.group(1)), int(m.group(2)) if m.group(2) else 0, now))
    ]

    for pattern, calc_func in smart_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            datetime_obj = calc_func(match)
            if datetime_obj:
                clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
                return datetime_obj, clean_text

    # Relative time patterns
    relative_patterns = [
        (r'en\s+(\d+)\s*m(?:in)?(?:utos?)?', lambda m: now + timedelta(minutes=int(m.group(1)))),
        (r'en\s+(\d+)\s*h(?:oras?)?', lambda m: now + timedelta(hours=int(m.group(1)))),
        (r'en\s+(\d+)\s*d(?:ias?)?', lambda m: now + timedelta(days=int(m.group(1))))
    ]

    for pattern, calc_func in relative_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            datetime_obj = calc_func(match)
            clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
            return datetime_obj, clean_text

    # Try with dateparser
    # First try simple date patterns without specific time
    date_patterns_no_time = [
        r'\b(?:mañana|tomorrow)\b',
        r'\b(?:el\s+)?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b',
        r'\b(?:hoy|today)\b'
    ]

    # Search for specific date/time patterns (excluding those handled by smart patterns)
    date_patterns = [
        r'\b(?:mañana|tomorrow)\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?|\d{1,2}\s*de\s*la\s*(?:mañana|tarde|noche)|antes\s*de\s*las?\s*\d{1,2})',
        r'\b(?:el\s+)?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?)',
        r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?)?',  # Full dates with year
        r'\b\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}\b',
        r'\b(?:hoy|today)\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?)',
        r'\bantes\s*de\s*las?\s*\d{1,2}(?::\d{2})?\b',
        r'\b\d{1,2}:\d{2}\b'
    ]

    date_text = None
    remaining_text = text
    use_default_time = False

    # First search for patterns with specific time
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_text = match.group(0)
            # Process "antes de las X"
            if "antes de las" in date_text.lower():
                # Extract the hour from "antes de las X"
                hour_match = re.search(r'(\d{1,2})(?::\d{2})?', date_text)
                if hour_match:
                    hour = int(hour_match.group(1))
                    # If it says "antes de las 5 de la tarde", convert to 17:00
                    if "tarde" in text.lower() and hour <= 12:
                        hour += 12
                    # Create new date with specific time
                    base_date = re.search(r'\b(?:mañana|tomorrow|hoy|today)\b', date_text, re.IGNORECASE)
                    if base_date:
                        if base_date.group(0).lower() in ['mañana', 'tomorrow']:
                            date_base = (datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')) + timedelta(days=1)).strftime('%Y-%m-%d')
                        else:
                            date_base = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime('%Y-%m-%d')
                        date_text = f"{date_base} {hour-1}:00"  # One hour before
            remaining_text = text.replace(match.group(0), '').strip()
            break

    # If no pattern with time was found, search for date only
    if not date_text:
        for pattern in date_patterns_no_time:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_text = match.group(0)
                remaining_text = text.replace(date_text, '').strip()
                use_default_time = True
                break

    if not date_text:
        # Try parsing the entire text
        parsed_date = dateparser.parse(text, settings=DATEPARSER_SETTINGS)
        if parsed_date:
            # If it parses everything, assume no additional text
            return parsed_date, "recordatorio"
        return None, None

    # Parse the found date
    parsed_date = dateparser.parse(date_text, settings=DATEPARSER_SETTINGS)

    # If parsed but has no specific time, add 9am by default
    if parsed_date and use_default_time:
        parsed_date = parsed_date.replace(hour=9, minute=0, second=0, microsecond=0)

    if not parsed_date:
        return None, None

    # Ensure the date has timezone
    if parsed_date.tzinfo is None:
        parsed_date = pytz.timezone('America/Argentina/Buenos_Aires').localize(parsed_date)

    # Clean remaining text
    remaining_text = re.sub(r'^\s*que\s+', '', remaining_text, flags=re.IGNORECASE)
    remaining_text = remaining_text.strip()

    if not remaining_text:
        remaining_text = "recordatorio"

    return parsed_date, remaining_text

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot errors."""
    logger.error(f"Error: {context.error}")

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Ocurrió un error. Intenta nuevamente."
        )