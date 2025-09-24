import re
import logging
from datetime import datetime, timedelta
from typing import Tuple, List
import unicodedata
import pytz
import dateparser
from telegram import Update
from telegram.ext import ContextTypes
import db
import scheduler
from transcription import transcriber
from pdf_exporter import PDFExporter, cleanup_temp_file

logger = logging.getLogger(__name__)

# Configure dateparser for Spanish
DATEPARSER_SETTINGS = {
    'PREFER_DATES_FROM': 'future',
    'TIMEZONE': 'America/Argentina/Buenos_Aires',
    'DATE_ORDER': 'DMY',
    'DEFAULT_LANGUAGES': ['es']
}

def register_or_update_user(update: Update) -> int:
    """Register or update user information and return user_id."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    return db.create_or_update_user(
        chat_id=chat_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_bot=user.is_bot,
        language_code=user.language_code or 'es'
    )

def capitalize_first_letter(text: str) -> str:
    """Capitalize the first letter of a text while preserving the rest."""
    if not text:
        return text
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()

def normalize_text_for_search(text: str) -> str:
    """Normalize text for search: remove accents, convert to lowercase."""
    if not text:
        return ""

    # Remove accents/diacritics
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # Convert to lowercase
    return without_accents.lower()

def extract_conversational_search_terms(text: str) -> List[str]:
    """Extract search terms from conversational questions about people or topics.

    Examples:
    - "qué le gusta a Cindy?" → ["cindy", "gusta"]
    - "Cindy sugus" → ["cindy", "sugus"]
    - "dónde come Pedro?" → ["pedro", "come"]
    """
    # Normalize text for processing
    normalized = normalize_text_for_search(text)

    # Remove question words and common patterns
    question_words = [
        'que', 'quien', 'donde', 'cuando', 'como', 'por', 'para',
        'le', 'les', 'me', 'te', 'se', 'nos', 'el', 'la', 'los', 'las',
        'un', 'una', 'del', 'de', 'en', 'con', 'por', 'para', 'a',
        'y', 'o', 'pero', 'si', 'no', 'mas', 'muy', 'tan', 'tanto'
    ]

    # Split into words and filter
    words = normalized.split()
    search_terms = []

    for word in words:
        # Remove punctuation
        clean_word = re.sub(r'[^\w]', '', word)

        # Skip if empty, too short, or is a question word
        if len(clean_word) >= 3 and clean_word not in question_words:
            search_terms.append(clean_word)

    return search_terms

def extract_explicit_category(text: str) -> Tuple[str, str]:
    """Extract explicit category from text pattern like '(categoría: trabajo)' or '(categoria: trabajo)'.

    Returns:
        tuple: (cleaned_text, category) - text without the category pattern and the extracted category
    """
    # Pattern to match (categoría: X) or (categoria: X) - case insensitive
    pattern = r'\s*\(\s*categor[ií]a\s*:\s*([^)]+)\s*\)\s*$'

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        category = match.group(1).strip().lower()
        cleaned_text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
        return cleaned_text, category

    return text, None

def extract_category_from_text(text: str) -> str:
    """Extract category from text based on keywords."""
    text_lower = text.lower()

    # Work-related keywords
    work_keywords = ['trabajo', 'reunión', 'meeting', 'oficina', 'jefe', 'cliente', 'proyecto',
                     'presentación', 'deadline', 'entrega', 'equipo', 'empresa', 'negocio']
    if any(keyword in text_lower for keyword in work_keywords):
        return 'trabajo'

    # Health-related keywords
    health_keywords = ['médico', 'doctor', 'dr.', 'dr ', 'hospital', 'clínica', 'turno', 'consulta',
                       'medicina', 'pastilla', 'tratamiento', 'análisis', 'estudio', 'salud',
                       'dentista', 'odontólogo', 'psicólogo', 'terapia', 'farmacia', 'receta']
    if any(keyword in text_lower for keyword in health_keywords):
        return 'salud'

    # Personal/family keywords
    personal_keywords = ['cumpleaños', 'familia', 'mamá', 'papá', 'hermano', 'hermana', 'hijo',
                         'hija', 'esposo', 'esposa', 'novio', 'novia', 'amigo', 'personal',
                         'recomendó', 'recomienda', 'libro', 'sugiere', 'aconseja', 'le gusta',
                         'prefiere', 'odia', 'le encanta']
    if any(keyword in text_lower for keyword in personal_keywords):
        return 'personal'

    # Shopping/errands keywords
    shopping_keywords = ['comprar', 'supermercado', 'tienda', 'mercado', 'shopping', 'pagar',
                        'banco', 'farmacia', 'ferretería', 'verdulería']
    if any(keyword in text_lower for keyword in shopping_keywords):
        return 'compras'

    # Entertainment keywords
    entertainment_keywords = ['cine', 'película', 'teatro', 'concierto', 'partido', 'show',
                             'restaurante', 'bar', 'fiesta', 'vacaciones', 'viaje', 'música',
                             'banda', 'artista', 'baile', 'discoteca', 'pub', 'parrilla']
    if any(keyword in text_lower for keyword in entertainment_keywords):
        return 'entretenimiento'

    # Home/maintenance keywords
    home_keywords = ['casa', 'hogar', 'limpieza', 'limpiar', 'cocinar', 'cocina', 'jardín',
                     'plantas', 'mascotas', 'perro', 'gato', 'reparar', 'arreglar', 'filtro',
                     'aire acondicionado', 'calefacción', 'electricidad', 'plomería', 'mantenimiento']
    if any(keyword in text_lower for keyword in home_keywords):
        return 'hogar'

    # Default category
    return 'general'

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    # Register or update user
    register_or_update_user(update)

    message = """
🤖 ¡Hola! Soy tu bot de recordatorios personal.

📝 **Cómo usarme:**

**Comandos:**
/recordar <fecha/hora> <texto> - Crear recordatorio
/lista - Ver recordatorios activos
/hoy - Ver recordatorios de hoy
/semana [todos] - Ver recordatorios pendientes de esta semana
/dia <fecha> - Ver recordatorios de fecha específica
/buscar <palabra> - Buscar recordatorios
/historial - Ver recordatorios pasados
/bitacora <texto> - Guardar nota en la bitácora
/listarBitacora - Ver todas las notas de la bitácora
/buscarBitacora <palabra> - Buscar en la bitácora
/borrarBitacora <id|todos> - Eliminar nota(s) de la bitácora
/historialBitacora - Ver historial de entradas eliminadas
/cancelar <id> - Cancelar recordatorio
/importante [intervalo] <fecha/hora> <texto> - Recordatorio que se repite
/completar <id> - Completar recordatorio importante
/exportar [completo] - Exportar todos los datos a PDF

**Ejemplos de comandos:**
• `/recordar mañana 18:00 comprar comida`
• `/recordar en 30m apagar el horno`
• `/recordar 2025-09-20 09:30 reunión con Juan`
• `/semana` - Ver solo recordatorios pendientes
• `/semana todos` - Ver todos los recordatorios
• `/exportar` - Exportar solo datos activos
• `/exportar completo` - Exportar incluyendo historial
• `/importante 10 mañana 9:00 ir al médico` (cada 10 min)
• `/importante lunes 15:00 reunión` (cada 5 min por defecto)
• `/completar 123` - Parar repetición del recordatorio #123
• `/bitacora No me gustó el vino en Bar Central`
• `/bitacora Si voy a La Parolaccia, pedir ravioles al pesto`

**Lenguaje natural:**
También puedes escribir directamente:
• "Mañana a las 2 recordame que tengo turno médico"
• "En 45 minutos recordame sacar la pizza"
• "El viernes a las 18hs haceme acordar de comprar cerveza"

**Mensajes de voz:** 🎙️
¡Envía mensajes de voz y los transcribiré automáticamente!
• "Recordame mañana comprar leche"
• "Nota que no me gustó el restaurante X"

¡Empezá a crear tus recordatorios! 🎯
    """

    await update.message.reply_text(message)

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /recordar command."""
    # Register or update user
    register_or_update_user(update)

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

        # Use fire emoji for important reminders
        if reminder.get('is_important', False):
            emoji = "🔥"
            repeat_info = f" (cada {reminder.get('repeat_interval', 5)}min)"
        else:
            emoji = "🔔"
            repeat_info = ""

        message += f"{emoji} **#{reminder['id']}** - {formatted_date}{repeat_info}\n"
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

        # Show different emoji and text based on status
        if reminder['status'] == 'sent':
            status_emoji = "✅"
            status_text = "(enviado)"
        else:
            status_emoji = "🔔"
            status_text = ""

        message += f"{status_emoji} **#{reminder['id']}** - {formatted_time} {status_text}\n"
        message += f"   {reminder['text']}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /semana command."""
    chat_id = update.effective_chat.id

    # Check if "todos" argument is provided
    include_sent = False
    if context.args and context.args[0].lower() == "todos":
        include_sent = True

    reminders = db.get_week_reminders(chat_id, include_sent)

    if not reminders:
        if include_sent:
            await update.message.reply_text("📅 No tienes recordatorios para esta semana.")
        else:
            await update.message.reply_text("📅 No tienes recordatorios pendientes para esta semana.")
        return

    # Group reminders by day
    from collections import defaultdict
    from datetime import datetime, timedelta
    import pytz

    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    now = datetime.now(timezone)

    # Create a dict to group reminders by day
    days_reminders = defaultdict(list)

    for reminder in reminders:
        # Get the date (without time) as key
        reminder_date = reminder['datetime'].date()
        days_reminders[reminder_date].append(reminder)

    # Spanish day names
    day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

    # Set message header based on what we're showing
    if include_sent:
        message = "📅 **Tus recordatorios de esta semana (todos):**\n\n"
    else:
        message = "📅 **Tus recordatorios pendientes de esta semana:**\n\n"

    # Get start of week (Monday)
    days_since_monday = now.weekday()
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)

    # Iterate through each day of the week
    for i in range(7):
        current_day = week_start + timedelta(days=i)
        current_date = current_day.date()
        day_name = day_names[i]

        # Format date
        formatted_date = current_day.strftime("%d/%m")

        # Check if it's today
        if current_date == now.date():
            day_header = f"**{day_name} {formatted_date} (HOY)**"
        else:
            day_header = f"**{day_name} {formatted_date}**"

        # Get reminders for this day
        day_reminders = days_reminders.get(current_date, [])

        if day_reminders:
            message += f"{day_header}\n"
            for reminder in day_reminders:
                formatted_time = reminder['datetime'].strftime("%H:%M")

                # Show different emoji and text based on status
                if reminder['status'] == 'sent':
                    status_emoji = "✅"
                    status_text = "(enviado)"
                else:
                    status_emoji = "🔔"
                    status_text = ""

                message += f"  {status_emoji} **#{reminder['id']}** - {formatted_time} {status_text}\n"
                message += f"     {reminder['text']}\n"
            message += "\n"
        else:
            # Only show empty days if they haven't passed yet or are today
            if current_date >= now.date():
                message += f"{day_header}\n"
                message += f"  _Sin recordatorios_\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

def parse_search_query(query: str) -> Tuple[str, bool]:
    """Parse search query to detect category search.

    Returns:
        tuple: (search_term, is_category_search)
    """
    # Check for category: pattern
    if query.startswith('categoria:') or query.startswith('categoría:'):
        category = query.split(':', 1)[1].strip()
        return category, True

    # Check for #category pattern
    if query.startswith('#'):
        category = query[1:].strip()
        return category, True

    return query, False

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /buscar command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /buscar <palabra o frase>\n"
            "Ejemplos:\n"
            "• /buscar comida\n"
            "• /buscar categoria:trabajo\n"
            "• /buscar #salud\n"
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

    # Parse search query
    search_term, is_category = parse_search_query(keyword)

    if is_category:
        reminders = db.search_reminders_by_category(chat_id, search_term)
        search_type = "categoría"
    else:
        reminders = db.search_reminders_fuzzy(chat_id, search_term)
        search_type = "palabra"

    if not reminders:
        await update.message.reply_text(f"🔍 No se encontraron recordatorios con {search_type}: \"{search_term}\"")
        return

    if is_category:
        message = f"🔍 **Recordatorios de categoría \"{search_term}\":**\n\n"
    else:
        message = f"🔍 **Recordatorios encontrados con \"{search_term}\":**\n\n"

    for reminder in reminders:
        formatted_date = reminder['datetime'].strftime("%d/%m/%Y %H:%M")

        # Highlight the keyword in the text (simple bold formatting) - only for text search
        if is_category:
            highlighted_text = reminder['text']
        else:
            highlighted_text = _highlight_keyword(reminder['text'], search_term)

        message += f"🔔 **#{reminder['id']}** - {formatted_date}\n"
        message += f"   {highlighted_text}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /dia command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /dia <fecha>\n"
            "Ejemplos:\n"
            "• /dia mañana\n"
            "• /dia ayer\n"
            "• /dia 22/09\n"
            "• /dia el lunes\n"
            "• /dia 25-12-2025"
        )
        return

    chat_id = update.effective_chat.id
    date_text = ' '.join(context.args)

    # Parse the date (allowing past dates for /dia command)
    target_date = _parse_date_only_with_past(date_text)

    if not target_date:
        await update.message.reply_text(
            "❌ No pude entender la fecha. Ejemplos:\n"
            "• mañana\n"
            "• ayer\n"
            "• 22/09\n"
            "• el viernes\n"
            "• 25-12-2025"
        )
        return

    # Get reminders for that date
    reminders = db.get_date_reminders(chat_id, target_date)

    # Format date for display
    formatted_date = target_date.strftime("%d/%m/%Y")
    weekday = target_date.strftime("%A")

    # Translate weekday to Spanish
    weekday_spanish = {
        'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
        'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    weekday = weekday_spanish.get(weekday, weekday)

    if not reminders:
        await update.message.reply_text(f"📅 No tienes recordatorios para el {weekday} {formatted_date}.")
        return

    message = f"📅 **Recordatorios para {weekday} {formatted_date}:**\n\n"

    for reminder in reminders:
        # Show only time for same-day reminders
        formatted_time = reminder['datetime'].strftime("%H:%M")
        message += f"🔔 **#{reminder['id']}** - {formatted_time}\n"
        message += f"   {reminder['text']}\n\n"

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

async def vault_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /historialBitacora command."""
    chat_id = update.effective_chat.id
    entries = db.get_vault_history(chat_id)

    if not entries:
        await update.message.reply_text("📖 No hay entradas eliminadas en el historial de la bitácora")
        return

    message = f"🗂️ **Historial de bitácora (eliminadas):**\n\n"

    for entry in entries:
        created_date = entry['created_at'].strftime("%d/%m/%Y")
        deleted_date = entry['deleted_at'].strftime("%d/%m/%Y") if entry['deleted_at'] else "N/A"

        message += f"🗑️ **#{entry['id']}** - Creada: {created_date} | Eliminada: {deleted_date} [#{entry['category']}]\n"
        message += f"   {entry['text']}\n\n"

    message += f"_(Mostrando últimas {len(entries)} entradas eliminadas)_"
    await update.message.reply_text(message, parse_mode='Markdown')

async def vault_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /bitacora command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /bitacora <texto>\n"
            "Ejemplo: /bitacora No me gustó el vino en Bar Central"
        )
        return

    chat_id = update.effective_chat.id
    text = ' '.join(context.args)

    if not text.strip():
        await update.message.reply_text("❌ El texto de la bitácora no puede estar vacío.")
        return

    # Extract explicit category if present
    text, explicit_category = extract_explicit_category(text)

    # Capitalize first letter
    text = capitalize_first_letter(text)

    # Use explicit category or extract from text
    category = explicit_category if explicit_category else extract_category_from_text(text)
    vault_id = db.add_vault_entry(chat_id, text, category)
    await update.message.reply_text(f"📖 Guardado en la bitácora (#{vault_id}): \"{text}\" [#{category}]")

async def vault_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /listar bitacora command."""
    chat_id = update.effective_chat.id
    entries = db.get_vault_entries(chat_id)

    if not entries:
        await update.message.reply_text("📖 Tu bitácora está vacía.")
        return

    message = "📖 **Tu bitácora:**\n\n"

    for entry in entries:
        formatted_date = entry['created_at'].strftime("%d/%m/%Y")
        message += f"📝 **#{entry['id']}** - {formatted_date}\n"
        message += f"   {entry['text']}\n\n"

    message += f"_(Total: {len(entries)} entradas)_"
    await update.message.reply_text(message, parse_mode='Markdown')

async def vault_search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /buscar bitacora command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /buscar bitacora <palabra>\n"
            "Ejemplos:\n"
            "• /buscar bitacora vino\n"
            "• /buscar bitacora categoria:bares\n"
            "• /buscar bitacora #entretenimiento"
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

    # Parse search query
    search_term, is_category = parse_search_query(keyword)

    if is_category:
        entries = db.search_vault_by_category(chat_id, search_term)
        search_type = "categoría"
    else:
        entries = db.search_vault_fuzzy(chat_id, search_term)
        search_type = "palabra"

    if not entries:
        await update.message.reply_text(f"🔍 No se encontraron entradas en la bitácora con {search_type}: \"{search_term}\"")
        return

    if is_category:
        message = f"🔍 **Bitácora - Categoría \"{search_term}\":**\n\n"
    else:
        message = f"🔍 **Bitácora - Entradas encontradas con \"{search_term}\":**\n\n"

    for entry in entries:
        formatted_date = entry['created_at'].strftime("%d/%m/%Y")

        # Highlight the keyword in the text - only for text search
        if is_category:
            highlighted_text = entry['text']
        else:
            highlighted_text = _highlight_keyword(entry['text'], search_term)

        message += f"📝 **#{entry['id']}** - {formatted_date}\n"
        message += f"   {highlighted_text}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def vault_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /borrarBitacora command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /borrarBitacora <id|todos>\n"
            "Ejemplos:\n"
            "• /borrarBitacora 5\n"
            "• /borrarBitacora todos"
        )
        return

    chat_id = update.effective_chat.id
    arg = context.args[0].lower()

    if arg == "todos":
        # Delete all vault entries
        deleted_count = db.delete_all_vault_entries(chat_id)
        if deleted_count > 0:
            await update.message.reply_text(f"🗑️ Se eliminaron {deleted_count} entradas de la bitácora")
        else:
            await update.message.reply_text("📖 Tu bitácora ya estaba vacía")
        return

    try:
        vault_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ El ID debe ser un número o 'todos'.")
        return

    if db.delete_vault_entry(chat_id, vault_id):
        await update.message.reply_text(f"🗑️ Entrada #{vault_id} eliminada de la bitácora")
    else:
        await update.message.reply_text(f"❌ No se encontró la entrada #{vault_id} en tu bitácora")

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
    # Register or update user
    register_or_update_user(update)

    # Check if we're waiting for girlfriend validation
    if context.user_data.get('pending_girlfriend_validation'):
        await process_girlfriend_validation(update, context)
        return

    # Check if we're waiting for admin validation
    if context.user_data.get('pending_admin_validation'):
        await process_admin_validation(update, context)
        return

    # Check if we're waiting for surprise upload (admin photo upload)
    if context.user_data.get('waiting_for_surprise_upload'):
        handled = await handle_surprise_upload(update, context)
        if handled:
            return

    text = update.message.text.lower()

    # Check if it's a reminder attempt
    keywords = ['recordar', 'recordame', 'aviso', 'avisame', 'haceme acordar', 'acordar']

    # Check if it's a vault entry (bitácora)
    vault_keywords = ['anotá', 'anota', 'nota que', 'apuntar que', 'recordar que', 'acordarme que', 'guardar que']
    # Also check normalized text for accent variations
    normalized_text = normalize_text_for_search(text)
    vault_keywords_normalized = [normalize_text_for_search(kw) for kw in vault_keywords]

    if any(keyword in text for keyword in vault_keywords) or any(keyword in normalized_text for keyword in vault_keywords_normalized):
        # Remove vault keywords and save to vault
        clean_text = update.message.text
        for keyword in vault_keywords:
            clean_text = re.sub(rf'\b{keyword}\b', '', clean_text, flags=re.IGNORECASE)
        clean_text = clean_text.strip()

        if clean_text:
            # Extract explicit category if present
            clean_text, explicit_category = extract_explicit_category(clean_text)

            # Capitalize first letter
            clean_text = capitalize_first_letter(clean_text)
            chat_id = update.effective_chat.id

            # Use explicit category or extract from text
            category = explicit_category if explicit_category else extract_category_from_text(clean_text)
            vault_id = db.add_vault_entry(chat_id, clean_text, category)
            await update.message.reply_text(f"📖 Guardado en la bitácora (#{vault_id}): \"{clean_text}\" [#{category}]")
        else:
            await update.message.reply_text("❌ El texto de la bitácora no puede estar vacío.")
        return

    # Check for conversational questions about bitácora (e.g., "qué le gusta a Cindy?")
    elif '?' in text and any(word in text for word in ['que', 'quien', 'donde', 'cuando', 'como']):
        chat_id = update.effective_chat.id
        # Extract search terms from conversational question
        search_terms = extract_conversational_search_terms(text)

        if search_terms:
            entries = db.search_vault_conversational(chat_id, search_terms)

            if not entries:
                terms_str = ", ".join(search_terms)
                await update.message.reply_text(f"🤔 No encontré información sobre: {terms_str}")
                return

            message = f"🔍 **Esto es lo que sé sobre tu consulta:**\n\n"

            for entry in entries[:5]:  # Limit to top 5 results
                formatted_date = entry['created_at'].strftime("%d/%m/%Y")
                score_emoji = "🎯" if entry['score'] >= 2 else "📝"

                message += f"{score_emoji} **#{entry['id']}** - {formatted_date}\n"
                message += f"   {entry['text']}\n\n"

            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text("🤔 No pude entender tu pregunta. Intenta ser más específico.")
        return

    # Check if it's a bitácora search using "Averigua" (with or without accent)
    elif text.startswith('averigua') or normalize_text_for_search(text).startswith('averigua'):
        chat_id = update.effective_chat.id
        # Handle both "averigua" and "averiguá"
        if text.startswith('averigua'):
            search_query = text[8:].strip()  # Remove "averigua" and clean
        else:
            search_query = text[9:].strip()  # Remove "averiguá" and clean
        if search_query:
            # Parse search query for category or text search
            search_term, is_category = parse_search_query(search_query)

            # Always split search term to check for multiple terms
            search_terms = search_term.split()

            if is_category:
                entries = db.search_vault_by_category(chat_id, search_term)
                search_type = "categoría"
            elif len(search_terms) > 1:
                # Use conversational search for multiple terms
                normalized_terms = [normalize_text_for_search(term) for term in search_terms]
                entries = db.search_vault_conversational(chat_id, normalized_terms)
                search_type = f"términos: {', '.join(search_terms)}"
            else:
                # Single term search
                entries = db.search_vault_fuzzy(chat_id, search_term)
                search_type = "texto"

            if not entries:
                if len(search_terms) > 1:
                    await update.message.reply_text(f"🔍 No encontré nada en tu bitácora con {search_type}")
                else:
                    await update.message.reply_text(f"🔍 No encontré nada en tu bitácora con {search_type}: \"{search_term}\"")
                return

            if is_category:
                message = f"🔍 **Bitácora - Categoría \"{search_term}\":**\n\n"
            elif len(search_terms) > 1:
                message = f"🔍 **Bitácora - Búsqueda con {search_type}:**\n\n"
            else:
                message = f"🔍 **Bitácora - Búsqueda \"{search_term}\":**\n\n"

            for entry in entries:
                formatted_date = entry['created_at'].strftime("%d/%m/%Y")

                # Highlight the keyword in the text - only for text search
                if is_category:
                    highlighted_text = entry['text']
                    entry_emoji = "📝"
                elif len(search_terms) > 1:
                    # For multiple terms, show the text as-is (highlighting multiple terms is complex)
                    highlighted_text = entry['text']
                    # Use score emoji instead of default 📝 if available
                    if 'score' in entry:
                        entry_emoji = "🎯" if entry['score'] >= 2 else "📝"
                    else:
                        entry_emoji = "📝"
                else:
                    highlighted_text = _highlight_keyword(entry['text'], search_term)
                    entry_emoji = "📝"

                message += f"{entry_emoji} **#{entry['id']}** - {formatted_date}\n"
                message += f"   {highlighted_text}\n\n"

            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "❌ Especifica qué averiguar.\n"
                "Ejemplos:\n"
                "• Averigua vino\n"
                "• Averigua categoria:bares\n"
                "• Averigua #entretenimiento"
            )
        return


    # Check if it's a reminder
    elif any(keyword in text for keyword in keywords):
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

    # Extract explicit category if present
    reminder_text, explicit_category = extract_explicit_category(reminder_text)

    # Capitalize first letter
    reminder_text = capitalize_first_letter(reminder_text)

    # Verify that the date is in the future
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
    if datetime_obj <= now:
        await update.message.reply_text("❌ La fecha debe ser en el futuro.")
        return

    # Use explicit category or extract from text
    category = explicit_category if explicit_category else extract_category_from_text(reminder_text)
    reminder_id = db.add_reminder(chat_id, reminder_text, datetime_obj, category)
    scheduler.schedule_reminder(
        context.bot, chat_id, reminder_id, reminder_text, datetime_obj
    )

    # Confirm to user
    formatted_date = datetime_obj.strftime("%d/%m/%Y %H:%M")
    await update.message.reply_text(
        f"✅ Dale, te aviso el {formatted_date}: \"{reminder_text}\" [#{category}] (ID #{reminder_id})"
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

def _smart_date_parse_with_past(day: int, month: int, now: datetime) -> datetime:
    """Parse day/month intelligently, allowing past dates (e.g., '22/09')."""
    if day < 1 or day > 31 or month < 1 or month > 12:
        return None

    # Always try current year first, regardless of whether it's past or future
    try:
        target_date = now.replace(year=now.year, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
        return target_date
    except ValueError:
        # If invalid for current year (e.g., Feb 30), try previous year
        try:
            target_date = now.replace(year=now.year - 1, month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
            return target_date
        except ValueError:
            return None

def _smart_day_parse_with_past(day: int, now: datetime) -> datetime:
    """Parse day of current month intelligently, allowing past dates."""
    if day < 1 or day > 31:
        return None

    try:
        # Try current month first
        target_date = now.replace(day=day, hour=0, minute=0, second=0, microsecond=0)
        return target_date
    except ValueError:
        return None

def _smart_weekday_day_parse_with_past(weekday_str: str, day: int, now: datetime) -> datetime:
    """Parse weekday + day combination, allowing past dates."""
    weekdays = {
        'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3,
        'viernes': 4, 'sabado': 5, 'domingo': 6
    }

    target_weekday = weekdays.get(weekday_str.lower())
    if target_weekday is None or day < 1 or day > 31:
        return None

    # Find the date that matches both weekday and day in current or previous months
    for month_offset in range(0, -12, -1):  # Check current and previous 12 months
        try:
            test_month = now.month + month_offset
            test_year = now.year

            # Handle year rollover
            while test_month <= 0:
                test_month += 12
                test_year -= 1
            while test_month > 12:
                test_month -= 12
                test_year += 1

            target_date = now.replace(year=test_year, month=test_month, day=day, hour=0, minute=0, second=0, microsecond=0)

            if target_date.weekday() == target_weekday:
                return target_date

        except ValueError:
            continue

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

def _smart_weekday_day_parse(weekday: str, day: int, now: datetime) -> datetime:
    """Parse weekday + day (e.g., 'lunes 29')."""
    if day < 1 or day > 31:
        return None

    # Map Spanish weekdays to numbers (Monday=0)
    weekdays = {
        'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3,
        'viernes': 4, 'sabado': 5, 'domingo': 6
    }

    target_weekday = weekdays.get(weekday.lower())
    if target_weekday is None:
        return None

    # Try current month first
    try:
        target_date = now.replace(day=day, hour=9, minute=0, second=0, microsecond=0)
        # Check if it's the right weekday
        if target_date.weekday() == target_weekday:
            # If it's in the past, try next month
            if target_date <= now:
                if now.month == 12:
                    target_date = target_date.replace(year=now.year + 1, month=1)
                else:
                    target_date = target_date.replace(month=now.month + 1)
            return target_date
    except ValueError:
        pass

    # Try next month
    try:
        if now.month == 12:
            target_date = now.replace(year=now.year + 1, month=1, day=day, hour=9, minute=0, second=0, microsecond=0)
        else:
            target_date = now.replace(month=now.month + 1, day=day, hour=9, minute=0, second=0, microsecond=0)

        if target_date.weekday() == target_weekday:
            return target_date
    except ValueError:
        pass

    return None

def _smart_next_weekday_parse(weekday: str, now: datetime) -> datetime:
    """Parse 'weekday que viene' (e.g., 'lunes que viene')."""
    # Map Spanish weekdays to numbers (Monday=0)
    weekdays = {
        'lunes': 0, 'martes': 1, 'miercoles': 2, 'jueves': 3,
        'viernes': 4, 'sabado': 5, 'domingo': 6
    }

    target_weekday = weekdays.get(weekday.lower())
    if target_weekday is None:
        return None

    # Calculate days until next occurrence of this weekday
    current_weekday = now.weekday()
    days_ahead = target_weekday - current_weekday

    # If it's the same weekday, go to next week
    if days_ahead <= 0:
        days_ahead += 7

    target_date = now + timedelta(days=days_ahead)
    target_date = target_date.replace(hour=9, minute=0, second=0, microsecond=0)

    return target_date

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

def _parse_date_only_with_past(text: str) -> datetime:
    """Parse a date string without extracting reminder text, allowing past dates."""
    import pytz

    # Clean text
    text = text.strip()

    # Get current time for smart inference
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

    # Handle "ayer" (yesterday)
    if 'ayer' in text.lower():
        return now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

    # Direct DD/MM or DD-MM pattern check first (most common case)
    date_pattern = r'^(\d{1,2})[\/-](\d{1,2})$'
    match = re.match(date_pattern, text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        return _smart_date_parse_with_past(day, month, now)

    # Other patterns with simpler regex
    smart_patterns = [
        # "el lunes 29" or "lunes 29" (weekday + day)
        (r'\b(?:el\s+)?(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+(\d{1,2})\b', lambda m: _smart_weekday_day_parse_with_past(m.group(1), int(m.group(2)), now)),
        # "el 20" (day of current month/year) - but not if it has / or -
        (r'^\b(?:el\s+)?(\d{1,2})\b$', lambda m: _smart_day_parse_with_past(int(m.group(1)), now))
    ]

    for pattern, calc_func in smart_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            datetime_obj = calc_func(match)
            if datetime_obj:
                return datetime_obj

    # Try with dateparser for natural language dates (allowing past)
    # But use our custom settings that respect DD/MM format
    parsed_date = dateparser.parse(text, settings={
        'DATE_ORDER': 'DMY',
        'PREFER_DAY_OF_MONTH': 'first',
        'STRICT_PARSING': False,
        'RETURN_AS_TIMEZONE_AWARE': True,
        'TIMEZONE': 'America/Argentina/Buenos_Aires'
    })

    if parsed_date:
        # If parsed but has no specific time, set to start of day
        parsed_date = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Ensure the date has timezone
        if parsed_date.tzinfo is None:
            parsed_date = pytz.timezone('America/Argentina/Buenos_Aires').localize(parsed_date)

        return parsed_date

    return None

def _parse_date_only(text: str) -> datetime:
    """Parse a date string without extracting reminder text."""
    import pytz

    # Clean text
    text = text.strip()

    # Get current time for smart inference
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

    # Smart patterns for intuitive date parsing (reusing existing logic)
    smart_patterns = [
        # "el lunes 29" or "lunes 29" (weekday + day) - HIGHER PRIORITY
        (r'\b(?:el\s+)?(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+(\d{1,2})\b', lambda m: _smart_weekday_day_parse(m.group(1), int(m.group(2)), now)),
        # "el lunes que viene" or "lunes que viene" - HIGHER PRIORITY
        (r'\b(?:el\s+)?(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+que\s+viene\b', lambda m: _smart_next_weekday_parse(m.group(1), now)),
        # "el 20" (day of current month/year)
        (r'\b(?:el\s+)?(\d{1,2})\b(?![\/\-:])', lambda m: _smart_day_parse(int(m.group(1)), now)),
        # "el 20/12" or "20/12" (day/month of current year)
        (r'\b(?:el\s+)?(\d{1,2})[\/-](\d{1,2})\b(?![\-:])', lambda m: _smart_date_parse(int(m.group(1)), int(m.group(2)), now))
    ]

    for pattern, calc_func in smart_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            datetime_obj = calc_func(match)
            if datetime_obj:
                return datetime_obj

    # Try with dateparser for natural language dates
    parsed_date = dateparser.parse(text, settings=DATEPARSER_SETTINGS)

    if parsed_date:
        # If parsed but has no specific time, set to start of day
        parsed_date = parsed_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Ensure the date has timezone
        if parsed_date.tzinfo is None:
            parsed_date = pytz.timezone('America/Argentina/Buenos_Aires').localize(parsed_date)

        return parsed_date

    return None

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
        # "el lunes 29" or "lunes 29" (weekday + day) - HIGHER PRIORITY
        (r'\b(?:el\s+)?(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+(\d{1,2})\b', lambda m: _smart_weekday_day_parse(m.group(1), int(m.group(2)), now)),
        # "el lunes que viene" or "lunes que viene" - HIGHER PRIORITY
        (r'\b(?:el\s+)?(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\s+que\s+viene\b', lambda m: _smart_next_weekday_parse(m.group(1), now)),
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

                # After finding a date, check if there's time info in remaining text
                time_match = re.search(r'\ba\s*las?\s+(\d{1,2})(?::(\d{2}))?\b', clean_text, re.IGNORECASE)
                if time_match:
                    hour = int(time_match.group(1))
                    minute = int(time_match.group(2)) if time_match.group(2) else 0

                    # Apply smart hour parsing if needed
                    if hour <= 12:
                        # Use the same smart hour logic
                        time_obj = _smart_hour_parse(hour, minute, datetime_obj)
                        if time_obj:
                            # Replace the date part but keep the time from smart parsing
                            datetime_obj = datetime_obj.replace(hour=time_obj.hour, minute=time_obj.minute)
                    else:
                        # Hour is already in 24h format
                        datetime_obj = datetime_obj.replace(hour=hour, minute=minute)

                    # Remove time pattern from clean text
                    clean_text = re.sub(r'\ba\s*las?\s+\d{1,2}(?::\d{2})?\b', '', clean_text, flags=re.IGNORECASE).strip()

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

async def important_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /importante command for important repeating reminders."""
    # Register or update user
    user_id = register_or_update_user(update)

    if not context.args:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n\n"
            "**Ejemplos:**\n"
            "• `/importante 10 mañana 9:00 ir al médico` (cada 10 min)\n"
            "• `/importante 5 en 2h llamar a Juan` (cada 5 min)\n"
            "• `/importante lunes 10:00 reunión` (cada 5 min por defecto)",
            parse_mode='Markdown'
        )
        return

    # Parse arguments
    args = context.args
    text = ' '.join(args)

    # Check if first argument is a number (repeat interval)
    repeat_interval = 5  # Default 5 minutes
    start_index = 0

    try:
        # If first argument is a number, use it as repeat interval
        if args[0].isdigit():
            repeat_interval = int(args[0])
            if repeat_interval < 1 or repeat_interval > 60:
                await update.message.reply_text("❌ El intervalo debe ser entre 1 y 60 minutos.")
                return
            start_index = 1
            text = ' '.join(args[1:])
    except (ValueError, IndexError):
        pass

    if not text.strip():
        await update.message.reply_text("❌ Debes especificar el texto del recordatorio.")
        return

    # Process the reminder like a normal one
    await process_important_reminder(update, context, text, repeat_interval)

async def process_important_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, repeat_interval: int):
    """Process an important reminder with repetition."""
    chat_id = update.effective_chat.id

    try:
        # Extract date and reminder text
        parsed_date, remaining_text = extract_date_and_text(text)

        if not parsed_date:
            await update.message.reply_text(
                "❌ No pude entender la fecha/hora. Intenta con:\n"
                "• `mañana 9:00`\n"
                "• `en 2 horas`\n"
                "• `lunes 15:30`"
            )
            return

        # Extract category if present
        remaining_text, explicit_category = extract_explicit_category(remaining_text)

        # Capitalize first letter
        remaining_text = capitalize_first_letter(remaining_text)

        # Use explicit category or extract from text
        category = explicit_category if explicit_category else extract_category_from_text(remaining_text)

        # Create important reminder in database
        reminder_id = db.add_important_reminder(
            chat_id=chat_id,
            text=remaining_text,
            datetime_obj=parsed_date,
            category=category,
            repeat_interval=repeat_interval
        )

        # Schedule the reminder
        scheduler.schedule_important_reminder(reminder_id, parsed_date, repeat_interval, context.bot)

        # Format response
        formatted_time = parsed_date.strftime('%d/%m/%Y %H:%M')
        await update.message.reply_text(
            f"🔥 **Recordatorio importante creado:**\n"
            f"📅 **Fecha:** {formatted_time}\n"
            f"🔔 **Texto:** {remaining_text}\n"
            f"⏰ **Se repetirá cada:** {repeat_interval} minutos\n"
            f"🆔 **ID:** #{reminder_id}\n"
            f"📂 **Categoría:** #{category}\n\n"
            f"💡 Usa `/completar {reminder_id}` para detener la repetición.",
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error processing important reminder: {e}")
        await update.message.reply_text("❌ Error procesando el recordatorio importante. Intenta nuevamente.")

async def complete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /completar command to stop important reminder repetition."""
    # Register or update user
    user_id = register_or_update_user(update)
    chat_id = update.effective_chat.id

    if not context.args:
        await update.message.reply_text(
            "❌ Debes especificar el ID del recordatorio.\n\n"
            "**Ejemplo:** `/completar 123`",
            parse_mode='Markdown'
        )
        return

    try:
        reminder_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ El ID debe ser un número.")
        return

    # Mark as completed
    success = db.complete_important_reminder(chat_id, reminder_id)

    if success:
        await update.message.reply_text(f"✅ Recordatorio importante #{reminder_id} completado. ¡No se repetirá más!")

        # Cancel from scheduler
        scheduler.cancel_reminder(reminder_id)
    else:
        await update.message.reply_text(f"❌ No se encontró un recordatorio importante activo con ID #{reminder_id}.")

async def girlfriend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /novia command to activate girlfriend mode."""
    # Register or update user
    user_id = register_or_update_user(update)
    chat_id = update.effective_chat.id

    # Check if already activated
    if db.is_girlfriend(chat_id):
        await update.message.reply_text(
            "💕 Ya tenés el modo especial activado, mi amor! ✨\n\n"
            "Podés usar todos los comandos románticos 🥰"
        )
        return

    # Ask the secret question
    await update.message.reply_text(
        "Para activar el modo especial, necesito que me digas algo...\n\n"
        "🎵 **Frase que más se me viene a la cabeza cuando te abrazo** (pedacito de canción):"
    )

    # We'll handle the answer in the free_message handler
    # Mark this chat as pending girlfriend validation
    context.user_data['pending_girlfriend_validation'] = True

def normalize_girlfriend_answer(text: str) -> str:
    """Normalize text for girlfriend validation - lowercase and remove accents."""
    if not text:
        return ""

    # Convert to lowercase
    normalized = text.lower()

    # Remove accents/diacritics using unicodedata
    normalized = unicodedata.normalize('NFD', normalized)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    return normalized

def validate_girlfriend_answer(text: str) -> bool:
    """Check if the answer contains the required romantic phrase."""
    normalized_text = normalize_girlfriend_answer(text)

    # Required words from "oh mi amor estás maravillosa hoy"
    required_words = ['oh', 'mi', 'amor', 'estas', 'maravillosa', 'hoy']

    # Check if all required words are present (order doesn't matter)
    return all(word in normalized_text for word in required_words)

async def process_girlfriend_validation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process girlfriend validation answer."""
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if validate_girlfriend_answer(user_text):
        # Correct answer! Activate girlfriend mode
        success = db.set_girlfriend_mode(chat_id)

        if success:
            await update.message.reply_text(
                "🥰KEASHEEEEE\n\n"
                "Hola culo 💕\n\n"
                "🌟 Ahora tenés acceso a comandos especiales:\n"
                "• `/fortuna` - Tu fortuna del día\n"
                "• `/sorpresa` - Una sorpresita\n\n"
                "Te amo muchísimo"
            )
        else:
            await update.message.reply_text("❌ Hubo un error activando el modo especial. Intenta de nuevo.")
    else:
        # Incorrect answer
        await update.message.reply_text(
            "💔 Mmm, no es exactamente lo que esperaba...\n\n"
            "💭 Pensá en esa frase que cantamos juntos cuando nos abrazamos 🎵\n\n"
            "Intentá de nuevo con `/novia` 💕"
        )

    # Clear the validation flag
    context.user_data.pop('pending_girlfriend_validation', None)

async def fortune_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /fortuna command - romantic fortune messages for girlfriend."""
    # Register or update user
    user_id = register_or_update_user(update)
    chat_id = update.effective_chat.id

    # Check if user has girlfriend mode activated
    if not db.is_girlfriend(chat_id):
        await update.message.reply_text(
            "🔒 Este comando es especial y requiere activación.\n\n"
            "Usá `/novia` para acceder a los comandos románticos 💕"
        )
        return

    # Romantic fortune messages
    # DEV NOTES: Modify this messages to be more personal
    romantic_fortunes = [
        "Hoy alguien que te ama piensa en vos más de lo normal 💕",
        "Tu sonrisa va a iluminar el día de alguien especial ✨",
        "Algo hermoso te espera hoy, y yo también 😘",
        "El universo conspira para que tengás un día perfecto 🌟",
        "Hoy vas a recibir una sorpresa de quien más te ama 💖",
        "Tu felicidad es el regalo más lindo que existe 🎁",
        "Alguien está pensando en abrazarte en este momento 🤗",
        "Hoy es un día perfecto para ser la persona más linda del mundo 👑",
        "Tu risa va a ser la melodía más bella de hoy 🎵",
        "Algo mágico va a pasar hoy, y vos sos la magia ✨",
        "El amor verdadero te rodea todo el tiempo 💕",
        "Hoy vas a brillar más que las estrellas 🌟",
        "Alguien te extraña muchísimo ahora mismo 💔💕",
        "Tu corazón va a estar lleno de alegría hoy 💖",
        "Hoy es el día perfecto para ser mimada 🥰",
        "La suerte está de tu lado, especialmente en el amor 🍀💕",
        "Algo dulce te espera al final del día 🍯",
        "Tu belleza interior y exterior brillan hoy 💎",
        "Alguien está escribiendo tu nombre en las estrellas ⭐",
        "Hoy vas a hacer que alguien se sienta el más afortunado 🎰💕",
        "El día tiene preparado algo especial para vos 🌈",
        "Tu energía positiva va a contagiar a todos 🌞",
        "Alguien cuenta los minutos hasta verte 🕐💕",
        "Hoy vas a recibir todo el amor que merecés 💖",
        "La vida te va a sorprender con algo hermoso 🌺",
        "Tu presencia hace que todo sea mejor 💫",
        "Hoy alguien va a decirte lo importante que sos 💕",
        "El amor que das vuelve a vos multiplicado 💞",
        "Hoy es tu día para brillar como la estrella que sos ⭐",
        "Algo que esperás va a llegar pronto 🙏💕"
    ]

    # Select a random fortune
    import random
    selected_fortune = random.choice(romantic_fortunes)

    # Send the fortune with romantic formatting
    await update.message.reply_text(
        f"🔮✨ **Tu Fortuna del Día** ✨🔮\n\n"
        f"💕 {selected_fortune}\n\n"
        f"🌟 _Con todo mi amor_ 🌟"
    )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /admin command to activate admin mode."""
    # Register or update user
    user_id = register_or_update_user(update)
    chat_id = update.effective_chat.id

    # Check if already activated
    if db.is_admin(chat_id):
        gallery_count = db.get_secret_gallery_count()
        waiting_upload = context.user_data.get('waiting_for_surprise_upload', False)

        await update.message.reply_text(
            "🔧 Ya tenés el modo administrador activado.\n\n"
            "Comandos de admin disponibles:\n"
            "• `/subir_sorpresa` - Subir foto para galería secreta\n\n"
            f"📊 **Estado Debug:**\n"
            f"• Fotos en galería: {gallery_count}\n"
            f"• Esperando subida: {'Sí' if waiting_upload else 'No'}\n"
            f"• Chat ID: {chat_id}"
        )
        return

    # Ask for admin password
    await update.message.reply_text(
        "🔐 **Acceso de Administrador**\n\n"
        "Ingresá la contraseña de administrador:"
    )

    # Mark this chat as pending admin validation
    context.user_data['pending_admin_validation'] = True

def validate_admin_password(password: str) -> bool:
    """Check if the admin password is correct."""
    return password.strip() == "admin6143"

async def process_admin_validation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process admin validation password."""
    chat_id = update.effective_chat.id
    user_password = update.message.text

    if validate_admin_password(user_password):
        # Correct password! Activate admin mode
        success = db.set_admin_mode(chat_id)

        if success:
            await update.message.reply_text(
                "🔧✅ **Modo Administrador Activado** ✅🔧\n\n"
                "🎛️ Comandos de administrador disponibles:\n"
                "• `/subir_sorpresa` - Subir foto/meme para galería secreta\n"
                "• Más comandos de admin próximamente...\n\n"
                "🔒 Acceso total concedido"
            )
        else:
            await update.message.reply_text("❌ Error activando el modo administrador. Intenta de nuevo.")
    else:
        # Incorrect password
        await update.message.reply_text(
            "❌ **Contraseña incorrecta**\n\n"
            "🔒 Acceso denegado. Intenta nuevamente con `/admin`"
        )

    # Clear the validation flag
    context.user_data.pop('pending_admin_validation', None)

async def upload_surprise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /subir_sorpresa command - upload photos for secret gallery (admin only)."""
    # Register or update user
    user_id = register_or_update_user(update)
    chat_id = update.effective_chat.id

    logger.info(f"Upload surprise command called by chat_id: {chat_id}")

    # Check if user has admin mode activated
    if not db.is_admin(chat_id):
        logger.warning(f"Non-admin user {chat_id} tried to use upload surprise command")
        await update.message.reply_text(
            "🔒 Este comando requiere privilegios de administrador.\n\n"
            "Usá `/admin` para acceder a los comandos de administración 🔧"
        )
        return

    gallery_count = db.get_secret_gallery_count()
    logger.info(f"Admin {chat_id} accessing upload surprise. Gallery count: {gallery_count}")

    await update.message.reply_text(
        f"📸 **Subir Sorpresa a Galería Secreta** 📸\n\n"
        f"📊 Fotos actuales en galería: {gallery_count}\n\n"
        f"📤 Enviá una foto, meme, sticker o documento y se agregará automáticamente a la galería secreta.\n\n"
        f"💡 También podés incluir una descripción opcional escribiendo texto junto con la imagen."
    )

    # Mark this chat as waiting for photo upload
    context.user_data['waiting_for_surprise_upload'] = True
    logger.info(f"Set waiting_for_surprise_upload flag for chat_id: {chat_id}")

async def surprise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /sorpresa command - send random photo from secret gallery (girlfriend only)."""
    # Register or update user
    user_id = register_or_update_user(update)
    chat_id = update.effective_chat.id

    # Check if user has girlfriend mode activated
    if not db.is_girlfriend(chat_id):
        await update.message.reply_text(
            "🔒 Este comando es especial y requiere activación.\n\n"
            "Usá `/novia` para acceder a los comandos románticos 💕"
        )
        return

    # Get a random photo from the gallery
    random_photo = db.get_random_secret_photo()

    if not random_photo:
        await update.message.reply_text(
            "😔 La galería secreta está vacía por ahora...\n\n"
            "¡Pero pronto habrá sorpresas esperándote! 💕✨"
        )
        return

    # Send the photo from local file
    try:
        import os

        local_file_path = random_photo['local_file_path']

        # Check if file exists
        if not os.path.exists(local_file_path):
            logger.error(f"Local file not found: {local_file_path}")
            # Mark as invalid and try to get another photo
            db.mark_photo_invalid(random_photo['id'])

            # Try to get another photo
            another_photo = db.get_random_secret_photo()
            if another_photo and os.path.exists(another_photo['local_file_path']):
                random_photo = another_photo
                local_file_path = random_photo['local_file_path']
            else:
                await update.message.reply_text(
                    "😔 No hay sorpresas disponibles por ahora...\n\n"
                    "¡Pedí al admin que suba nuevas fotos! 💕✨"
                )
                return

        caption = (f"🎁✨ **¡Sorpresa!** ✨🎁\n\n"
                  f"💕 {random_photo['description'] or 'Una sorpresita especial para vos'} 💕")

        if random_photo['file_type'] == 'photo':
            with open(local_file_path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_file,
                    caption=caption
                )
        elif random_photo['file_type'] == 'document':
            with open(local_file_path, 'rb') as doc_file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=doc_file,
                    caption=caption,
                    filename=random_photo['original_filename']
                )
        elif random_photo['file_type'] == 'sticker':
            with open(local_file_path, 'rb') as sticker_file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=sticker_file,
                    filename=random_photo['original_filename']
                )
                await update.message.reply_text(caption)
        else:
            # Fallback for other file types
            with open(local_file_path, 'rb') as file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=file,
                    caption=caption,
                    filename=random_photo['original_filename']
                )

    except Exception as e:
        logger.error(f"Error sending surprise photo from local file: {e}")
        await update.message.reply_text(
            "😅 Hubo un problemita enviando la sorpresa...\n\n"
            "¡Pero el amor está ahí! Intenta de nuevo 💕"
        )

async def handle_surprise_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo/document uploads for secret gallery when admin is in upload mode."""
    import os
    import uuid
    from pathlib import Path

    chat_id = update.effective_chat.id

    logger.info(f"Handle surprise upload called for chat_id: {chat_id}")
    logger.info(f"waiting_for_surprise_upload flag: {context.user_data.get('waiting_for_surprise_upload')}")

    # Check if we're waiting for a surprise upload
    if not context.user_data.get('waiting_for_surprise_upload'):
        logger.info(f"Not waiting for surprise upload from chat_id: {chat_id}")
        return False  # Not handling this message

    # Check admin privileges
    if not db.is_admin(chat_id):
        logger.warning(f"Non-admin user {chat_id} tried to upload surprise")
        context.user_data.pop('waiting_for_surprise_upload', None)
        return False

    logger.info(f"Processing surprise upload from admin {chat_id}")

    file_obj = None
    file_type = None
    original_filename = None
    description = update.message.caption or ""

    # Determine file type and get file object
    logger.info(f"Message content - Photo: {bool(update.message.photo)}, Document: {bool(update.message.document)}, Sticker: {bool(update.message.sticker)}")

    if update.message.photo:
        logger.info(f"Processing photo upload")
        file_obj = await update.message.photo[-1].get_file()  # Get highest quality photo
        file_type = 'photo'
        file_extension = '.jpg'
        original_filename = f"photo_{uuid.uuid4().hex[:8]}.jpg"
    elif update.message.document:
        logger.info(f"Processing document upload: {update.message.document.file_name}")
        file_obj = await update.message.document.get_file()
        file_type = 'document'
        original_filename = update.message.document.file_name or f"document_{uuid.uuid4().hex[:8]}"
        file_extension = Path(original_filename).suffix or '.bin'
    elif update.message.sticker:
        logger.info(f"Processing sticker upload")
        file_obj = await update.message.sticker.get_file()
        file_type = 'sticker'
        file_extension = '.webp'
        original_filename = f"sticker_{uuid.uuid4().hex[:8]}.webp"

    if file_obj:
        try:
            # Create unique filename
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            local_file_path = os.path.join("secret_gallery", unique_filename)

            # Download and save file locally
            await file_obj.download_to_drive(local_file_path)

            # Add to secret gallery database
            photo_id = db.add_secret_photo(
                local_file_path=local_file_path,
                file_type=file_type,
                uploaded_by=chat_id,
                original_filename=original_filename,
                description=description
            )

            gallery_count = db.get_secret_gallery_count()

            await update.message.reply_text(
                f"✅ **Sorpresa agregada a la galería secreta!** ✅\n\n"
                f"🆔 ID de sorpresa: #{photo_id}\n"
                f"📊 Total en galería: {gallery_count} sorpresas\n"
                f"📝 Descripción: {description or 'Sin descripción'}\n"
                f"📁 Archivo guardado: {original_filename}\n\n"
                f"🎁 ¡Ya está lista para sorprender! 💕"
            )

            # Clear the upload waiting flag
            context.user_data.pop('waiting_for_surprise_upload', None)
            return True

        except Exception as e:
            logger.error(f"Error downloading/saving surprise file: {e}")
            await update.message.reply_text(
                "❌ Error guardando el archivo.\n\n"
                "Intentá de nuevo o contactá al administrador."
            )
            return True

    else:
        await update.message.reply_text(
            "❌ Por favor enviá una foto, documento o sticker.\n\n"
            "📱 Tipos soportados: fotos, documentos, stickers"
        )
        return True  # We handled it, but it was invalid

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export all user data to PDF."""
    # Register or update user
    user_id = register_or_update_user(update)
    chat_id = update.effective_chat.id

    # Show processing message
    await update.message.reply_text("📄 Generando exportación en PDF...")

    try:
        # Get user info
        user_info = db.get_user_info(chat_id)
        if not user_info:
            await update.message.reply_text("❌ No se pudo obtener la información del usuario.")
            return

        # Get all reminders (active, sent, cancelled)
        all_reminders = db.get_all_reminders_for_export(chat_id)

        # Get all vault entries (active and deleted)
        all_vault_entries = db.get_all_vault_entries_for_export(chat_id)

        # Check if user wants to include history
        include_history = False
        if context.args and len(context.args) > 0:
            include_history = context.args[0].lower() in ['completo', 'historial', 'todo', 'full']

        # Generate PDF
        exporter = PDFExporter()
        pdf_path = exporter.generate_export_pdf(
            chat_id=chat_id,
            user_info=user_info,
            reminders=all_reminders,
            vault_entries=all_vault_entries,
            include_history=include_history
        )

        # Send the PDF file
        with open(pdf_path, 'rb') as pdf_file:
            filename = f"exportacion_datos_{chat_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            await context.bot.send_document(
                chat_id=chat_id,
                document=pdf_file,
                filename=filename,
                caption="📋 Aquí tienes tu exportación completa de datos.\n\n"
                       "📝 Para incluir historial completo, usa: /exportar completo"
            )

        # Clean up temporary file
        cleanup_temp_file(pdf_path)

        # Send summary
        summary_text = f"✅ Exportación completada:\n"
        summary_text += f"📊 Recordatorios: {len(all_reminders)}\n"
        summary_text += f"📖 Entradas de bitácora: {len(all_vault_entries)}\n"
        if include_history:
            summary_text += f"📜 Incluye elementos eliminados/enviados"
        else:
            summary_text += f"📋 Solo elementos activos (usa '/exportar completo' para incluir historial)"

        await update.message.reply_text(summary_text)

    except Exception as e:
        logger.error(f"Error generating PDF export for chat {chat_id}: {e}")
        await update.message.reply_text(
            "❌ Error generando la exportación. Intenta nuevamente en unos momentos."
        )

async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages and transcribe them."""
    if not update.message.voice:
        return

    # Register or update user
    register_or_update_user(update)

    # Show typing indicator while processing
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Get the voice file
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        # Transcribe the voice message
        transcribed_text = await transcriber.download_and_transcribe(voice_file, context.bot)

        if not transcribed_text:
            await update.message.reply_text(
                "❌ No pude transcribir el mensaje de voz. Asegurate de que tengas configurada la API de OpenAI."
            )
            return

        # Show what was transcribed
        await update.message.reply_text(f"🎙️ **Transcribí:** \"{transcribed_text}\"", parse_mode='Markdown')

        # Process the transcribed text as a normal message
        # Check if it's a reminder or vault entry
        text_lower = transcribed_text.lower()

        # Check if it's a vault entry (keywords that suggest it's a note)
        vault_keywords = ['recordar que', 'acordarme que', 'nota que', 'apuntar que', 'guardar que', 'anotá']
        if any(keyword in text_lower for keyword in vault_keywords):
            # Remove vault keywords and save to vault
            clean_text = transcribed_text
            for keyword in vault_keywords:
                clean_text = re.sub(rf'\b{keyword}\b', '', clean_text, flags=re.IGNORECASE)
            clean_text = clean_text.strip()

            if clean_text:
                # Extract explicit category if present
                clean_text, explicit_category = extract_explicit_category(clean_text)

                # Capitalize first letter
                clean_text = capitalize_first_letter(clean_text)
                chat_id = update.effective_chat.id

                # Use explicit category or extract from text
                category = explicit_category if explicit_category else extract_category_from_text(clean_text)
                vault_id = db.add_vault_entry(chat_id, clean_text, category)
                await update.message.reply_text(f"📖 Guardado en la bitácora (#{vault_id}): \"{clean_text}\" [#{category}]")
            return

        # Check if it's a reminder attempt
        reminder_keywords = ['recordar', 'recordame', 'aviso', 'avisame', 'haceme acordar', 'acordar']
        if any(keyword in text_lower for keyword in reminder_keywords):
            await process_reminder(update, context, transcribed_text)
        else:
            # If it doesn't match any pattern, suggest what they can do
            await update.message.reply_text(
                "🤔 No estoy seguro si es un recordatorio o una nota. Puedes:\n"
                "• Para recordatorios: incluye fecha/hora (ej: 'recordame mañana...')\n"
                "• Para notas de la bitácora: di 'recordar que...' o 'nota que...'"
            )

    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error procesando el mensaje de voz. Intenta nuevamente."
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Handle bot errors."""
    logger.error(f"Error: {context.error}")

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Ocurrió un error. Intenta nuevamente."
        )