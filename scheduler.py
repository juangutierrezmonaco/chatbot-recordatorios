from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import logging
from datetime import datetime
import pytz
from telegram import Bot
import db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=pytz.timezone('America/Argentina/Buenos_Aires'))

def init_scheduler():
    """Inicializa el scheduler."""
    scheduler.start()
    logger.info("Scheduler iniciado")

async def enviar_recordatorio(bot: Bot, chat_id: int, recordatorio_id: int, texto: str):
    """Envía un recordatorio al usuario y marca como enviado en BD."""
    try:
        mensaje = f"⏰ Recordatorio (#{recordatorio_id}): {texto}"
        await bot.send_message(chat_id=chat_id, text=mensaje)
        db.marcar_recordatorio_enviado(recordatorio_id)
        logger.info(f"Recordatorio {recordatorio_id} enviado a chat {chat_id}")
    except Exception as e:
        logger.error(f"Error enviando recordatorio {recordatorio_id}: {e}")

def programar_recordatorio(bot: Bot, chat_id: int, recordatorio_id: int, texto: str, fecha_hora: datetime):
    """Programa un recordatorio en el scheduler."""
    job_id = f"recordatorio_{recordatorio_id}"

    scheduler.add_job(
        enviar_recordatorio,
        trigger=DateTrigger(run_date=fecha_hora),
        args=[bot, chat_id, recordatorio_id, texto],
        id=job_id,
        name=f"Recordatorio #{recordatorio_id}",
        misfire_grace_time=60
    )

    logger.info(f"Recordatorio {recordatorio_id} programado para {fecha_hora}")

def cancelar_job_recordatorio(recordatorio_id: int):
    """Cancela un job del scheduler."""
    job_id = f"recordatorio_{recordatorio_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Job {job_id} cancelado")
        return True
    except Exception as e:
        logger.warning(f"No se pudo cancelar job {job_id}: {e}")
        return False

def cargar_recordatorios_pendientes(bot: Bot):
    """Carga todos los recordatorios pendientes al reiniciar el bot."""
    recordatorios = db.obtener_todos_recordatorios_activos()
    ahora = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))

    for recordatorio in recordatorios:
        fecha_hora = recordatorio['fecha_hora']

        # Solo programar si la fecha es futura
        if fecha_hora > ahora:
            programar_recordatorio(
                bot,
                recordatorio['chat_id'],
                recordatorio['id'],
                recordatorio['texto'],
                fecha_hora
            )
        else:
            # Marcar como vencido si ya pasó la fecha
            db.marcar_recordatorio_enviado(recordatorio['id'])
            logger.info(f"Recordatorio {recordatorio['id']} vencido al reiniciar")

    logger.info(f"Cargados {len(recordatorios)} recordatorios pendientes")

def shutdown_scheduler():
    """Detiene el scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler detenido")