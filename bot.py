#!/usr/bin/env python3

import os
import logging
import sys
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import InvalidToken
import db
import scheduler
import handlers

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Función principal del bot."""

    # Obtener token del bot
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("❌ Variable de entorno TELEGRAM_TOKEN no encontrada")
        print("❌ Error: Define la variable de entorno TELEGRAM_TOKEN")
        print("Ejemplo: export TELEGRAM_TOKEN='tu_token_aqui'")
        sys.exit(1)

    try:
        # Inicializar base de datos
        db.init_db()
        logger.info("✅ Base de datos inicializada")

        # Inicializar scheduler
        scheduler.init_scheduler()
        logger.info("✅ Scheduler inicializado")

        # Crear aplicación
        application = Application.builder().token(token).build()

        # Registrar handlers de comandos
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("recordar", handlers.recordar_command))
        application.add_handler(CommandHandler("lista", handlers.lista_command))
        application.add_handler(CommandHandler("cancelar", handlers.cancelar_command))

        # Handler para mensajes libres (lenguaje natural)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.mensaje_libre
        ))

        # Handler de errores
        application.add_error_handler(handlers.error_handler)

        # Cargar recordatorios pendientes
        scheduler.cargar_recordatorios_pendientes(application.bot)
        logger.info("✅ Recordatorios pendientes cargados")

        logger.info("🚀 Bot iniciado correctamente")
        print("🤖 Bot de recordatorios iniciado")
        print("📋 Presiona Ctrl+C para detener")

        # Iniciar el bot
        application.run_polling(allowed_updates=['message'])

    except InvalidToken:
        logger.error("❌ Token de Telegram inválido")
        print("❌ Error: Token de Telegram inválido")
        print("Verifica que TELEGRAM_TOKEN sea correcto")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("🛑 Deteniendo bot...")
        print("\n🛑 Deteniendo bot...")

    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)

    finally:
        # Limpiar recursos
        try:
            scheduler.shutdown_scheduler()
            logger.info("✅ Scheduler detenido")
        except:
            pass

        logger.info("👋 Bot detenido")
        print("👋 Bot detenido correctamente")

if __name__ == '__main__':
    main()