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

# Configurar dateparser para español
DATEPARSER_SETTINGS = {
    'PREFER_DATES_FROM': 'future',
    'TIMEZONE': 'America/Argentina/Buenos_Aires',
    'DATE_ORDER': 'DMY',
    'LANGUAGES': ['es']
}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /start."""
    mensaje = """
🤖 ¡Hola! Soy tu bot de recordatorios personal.

📝 **Cómo usarme:**

**Comandos:**
/recordar <fecha/hora> <texto> - Crear recordatorio
/lista - Ver recordatorios activos
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

    await update.message.reply_text(mensaje)

async def recordar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /recordar."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /recordar <fecha/hora> <texto>\n"
            "Ejemplo: /recordar mañana 18:00 comprar comida"
        )
        return

    texto_completo = ' '.join(context.args)
    resultado = await procesar_recordatorio(update, texto_completo)

async def lista_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /lista."""
    chat_id = update.effective_chat.id
    recordatorios = db.obtener_recordatorios_activos(chat_id)

    if not recordatorios:
        await update.message.reply_text("📝 No tienes recordatorios activos.")
        return

    mensaje = "📋 **Tus recordatorios activos:**\n\n"

    for recordatorio in recordatorios:
        fecha_formateada = recordatorio['fecha_hora'].strftime("%d/%m/%Y %H:%M")
        mensaje += f"🔔 **#{recordatorio['id']}** - {fecha_formateada}\n"
        mensaje += f"   {recordatorio['texto']}\n\n"

    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def cancelar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja el comando /cancelar."""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: /cancelar <id>\n"
            "Ejemplo: /cancelar 3"
        )
        return

    try:
        recordatorio_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ El ID debe ser un número.")
        return

    chat_id = update.effective_chat.id

    if db.cancelar_recordatorio(chat_id, recordatorio_id):
        scheduler.cancelar_job_recordatorio(recordatorio_id)
        await update.message.reply_text(f"❌ Recordatorio #{recordatorio_id} cancelado")
    else:
        await update.message.reply_text(f"❌ No se encontró el recordatorio #{recordatorio_id}")

async def mensaje_libre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes en lenguaje natural."""
    texto = update.message.text.lower()

    # Verificar si es un intento de recordatorio
    palabras_clave = ['recordar', 'recordame', 'aviso', 'avisame', 'haceme acordar', 'acordar']

    if any(palabra in texto for palabra in palabras_clave):
        await procesar_recordatorio(update, update.message.text)
    else:
        await update.message.reply_text(
            "🤔 No entiendo. Usa /start para ver cómo crear recordatorios."
        )

async def procesar_recordatorio(update: Update, texto: str):
    """Procesa un recordatorio desde comando o lenguaje natural."""
    chat_id = update.effective_chat.id

    # Extraer fecha/hora y texto
    fecha_hora, texto_recordatorio = extraer_fecha_y_texto(texto)

    if not fecha_hora:
        await update.message.reply_text(
            "❌ No pude entender la fecha/hora. Ejemplos:\n"
            "• mañana 18:00\n"
            "• en 30 minutos\n"
            "• 20/09/2025 09:30"
        )
        return

    if not texto_recordatorio:
        await update.message.reply_text("❌ Falta el texto del recordatorio.")
        return

    # Verificar que la fecha sea futura
    ahora = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
    if fecha_hora <= ahora:
        await update.message.reply_text("❌ La fecha debe ser en el futuro.")
        return

    # Guardar en BD y programar
    recordatorio_id = db.agregar_recordatorio(chat_id, texto_recordatorio, fecha_hora)
    scheduler.programar_recordatorio(
        context.bot, chat_id, recordatorio_id, texto_recordatorio, fecha_hora
    )

    # Confirmar al usuario
    fecha_formateada = fecha_hora.strftime("%d/%m/%Y %H:%M")
    await update.message.reply_text(
        f"✅ Dale, te aviso el {fecha_formateada}: \"{texto_recordatorio}\" (ID #{recordatorio_id})"
    )

def extraer_fecha_y_texto(texto: str):
    """Extrae fecha/hora y texto del recordatorio."""

    # Limpiar texto
    texto = texto.strip()

    # Remover palabras de comando si existen
    texto = re.sub(r'^\/(recordar|recordar)\s*', '', texto, flags=re.IGNORECASE)

    # Remover palabras de solicitud
    palabras_solicitud = [
        'recordame', 'recordar', 'avisame', 'aviso', 'haceme acordar',
        'acordar', 'que', 'de que', 'de'
    ]

    for palabra in palabras_solicitud:
        texto = re.sub(rf'\b{palabra}\b', '', texto, flags=re.IGNORECASE)

    texto = re.sub(r'\s+', ' ', texto).strip()

    # Patrones de tiempo relativo
    patrones_relativos = [
        (r'en\s+(\d+)\s*m(?:in)?(?:utos?)?', lambda m: datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')) + timedelta(minutes=int(m.group(1)))),
        (r'en\s+(\d+)\s*h(?:oras?)?', lambda m: datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')) + timedelta(hours=int(m.group(1)))),
        (r'en\s+(\d+)\s*d(?:ias?)?', lambda m: datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')) + timedelta(days=int(m.group(1))))
    ]

    for patron, calc_func in patrones_relativos:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            fecha_hora = calc_func(match)
            texto_limpio = re.sub(patron, '', texto, flags=re.IGNORECASE).strip()
            return fecha_hora, texto_limpio

    # Intentar con dateparser
    # Buscar patrones de fecha/hora comunes
    patrones_fecha = [
        r'\b(?:mañana|tomorrow)\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?|\d{1,2}\s*de\s*la\s*(?:mañana|tarde|noche))',
        r'\b(?:el\s+)?(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?)',
        r'\b\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?)?',
        r'\b\d{4}-\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}\b',
        r'\b(?:hoy|today)\b.*?(?:\d{1,2}:\d{2}|\d{1,2}hs?)',
        r'\ba\s*las?\s*\d{1,2}(?::\d{2})?\b',
        r'\b\d{1,2}:\d{2}\b'
    ]

    texto_fecha = None
    texto_resto = texto

    for patron in patrones_fecha:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            texto_fecha = match.group(0)
            texto_resto = texto.replace(texto_fecha, '').strip()
            break

    if not texto_fecha:
        # Intentar parseando todo el texto
        fecha_parseada = dateparser.parse(texto, settings=DATEPARSER_SETTINGS)
        if fecha_parseada:
            # Si parsea todo, asumir que no hay texto adicional
            return fecha_parseada, "recordatorio"
        return None, None

    # Parsear la fecha encontrada
    fecha_parseada = dateparser.parse(texto_fecha, settings=DATEPARSER_SETTINGS)

    if not fecha_parseada:
        return None, None

    # Limpiar texto restante
    texto_resto = re.sub(r'^\s*que\s+', '', texto_resto, flags=re.IGNORECASE)
    texto_resto = texto_resto.strip()

    if not texto_resto:
        texto_resto = "recordatorio"

    return fecha_parseada, texto_resto

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Maneja errores del bot."""
    logger.error(f"Error: {context.error}")

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Ocurrió un error. Intenta nuevamente."
        )