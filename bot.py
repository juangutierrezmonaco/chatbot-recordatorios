#!/usr/bin/env python3

import os
import logging
import sys
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import InvalidToken
import db
import scheduler
import handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main bot function."""

    # Load environment variables from .env
    load_dotenv()

    # Get bot token
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_TOKEN environment variable not found")
        print("❌ Error: Define la variable de entorno TELEGRAM_TOKEN")
        print("Ejemplo: export TELEGRAM_TOKEN='tu_token_aqui'")
        sys.exit(1)

    try:
        # Initialize database
        db.init_db()
        logger.info("✅ Database initialized")

        # Initialize scheduler
        scheduler.init_scheduler()
        logger.info("✅ Scheduler initialized")

        # Create application
        application = Application.builder().token(token).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", handlers.start_command))
        application.add_handler(CommandHandler("recordar", handlers.remind_command))
        application.add_handler(CommandHandler("lista", handlers.list_command))
        application.add_handler(CommandHandler("hoy", handlers.today_command))
        application.add_handler(CommandHandler("manana", handlers.tomorrow_command))
        application.add_handler(CommandHandler("semana", handlers.week_command))
        application.add_handler(CommandHandler("dia", handlers.date_command))
        application.add_handler(CommandHandler("buscar", handlers.search_command))
        application.add_handler(CommandHandler("historial", handlers.history_command))
        application.add_handler(CommandHandler("bitacora", handlers.vault_command))
        # camelCase commands for mobile friendliness
        application.add_handler(CommandHandler("listarBitacora", handlers.vault_list_command))
        application.add_handler(CommandHandler("buscarBitacora", handlers.vault_search_command))
        application.add_handler(CommandHandler("borrarBitacora", handlers.vault_delete_command))
        application.add_handler(CommandHandler("historialBitacora", handlers.vault_history_command))
        application.add_handler(CommandHandler("cancelar", handlers.cancel_command))
        application.add_handler(CommandHandler("importante", handlers.important_command))
        application.add_handler(CommandHandler("completar", handlers.complete_command))
        application.add_handler(CommandHandler("repetir", handlers.repeat_command))
        application.add_handler(CommandHandler("explicar", handlers.explain_command))
        application.add_handler(CommandHandler("novia", handlers.girlfriend_command))
        application.add_handler(CommandHandler("fortuna", handlers.fortune_command))
        application.add_handler(CommandHandler("admin", handlers.admin_command))
        application.add_handler(CommandHandler("subirSorpresa", handlers.upload_surprise_command))
        application.add_handler(CommandHandler("sorpresa", handlers.surprise_command))
        application.add_handler(CommandHandler("exportar", handlers.export_command))

        # Handler for voice messages
        application.add_handler(MessageHandler(
            filters.VOICE,
            handlers.voice_message_handler
        ))

        # Handler for photos, documents, and stickers (for surprise upload)
        application.add_handler(MessageHandler(
            filters.PHOTO | filters.Document.ALL | filters.Sticker.ALL,
            handlers.handle_surprise_upload
        ))

        # Handler for free messages (natural language)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handlers.free_message
        ))

        # Error handler
        application.add_error_handler(handlers.error_handler)

        # Load pending reminders
        scheduler.load_pending_reminders(application.bot)
        logger.info("✅ Pending reminders loaded")

        # Schedule nightly summary of tomorrow's reminders (22:00)
        scheduler.schedule_daily_summary(application.bot)
        logger.info("✅ Daily summary scheduled")

        logger.info("🚀 Bot started successfully")
        print("🤖 Bot de recordatorios iniciado")
        print("📋 Presiona Ctrl+C para detener")

        # Start the bot
        application.run_polling(
            allowed_updates=['message'],
            drop_pending_updates=True,
            close_loop=False
        )

    except InvalidToken:
        logger.error("❌ Invalid Telegram token")
        print("❌ Error: Token de Telegram inválido")
        print("Verifica que TELEGRAM_TOKEN sea correcto")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("🛑 Stopping bot...")
        print("\n🛑 Deteniendo bot...")

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)

    finally:
        # Clean up resources
        try:
            scheduler.shutdown_scheduler()
            logger.info("✅ Scheduler stopped")
        except:
            pass

        logger.info("👋 Bot stopped")
        print("👋 Bot detenido correctamente")

if __name__ == '__main__':
    main()