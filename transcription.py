import os
import logging
import tempfile
from pathlib import Path

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

logger = logging.getLogger(__name__)

class VoiceTranscriber:
    """Handle voice message transcription using OpenAI Whisper."""

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize OpenAI client."""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not installed. Voice transcription will not work.")
            return

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not found. Voice transcription will not work.")
            return

        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")

    async def transcribe_voice_file(self, file_path: str, language: str = "es") -> str:
        """
        Transcribe a voice file to text.

        Args:
            file_path: Path to the audio file
            language: Language code (default: "es" for Spanish)

        Returns:
            Transcribed text or None if failed
        """
        if not self.client:
            logger.error("OpenAI client not initialized")
            return None

        try:
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text"
                )

            # Clean up the transcription
            text = transcript.strip()
            logger.info(f"Successfully transcribed audio: '{text[:50]}...'")
            return text

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    async def download_and_transcribe(self, telegram_file, bot) -> str:
        """
        Download Telegram voice message and transcribe it.

        Args:
            telegram_file: Telegram File object
            bot: Telegram Bot instance

        Returns:
            Transcribed text or None if failed
        """
        if not self.client:
            return None

        temp_file = None
        try:
            # Create temporary file for audio
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_path = temp_file.name

            # Download voice message from Telegram
            await telegram_file.download_to_drive(temp_path)
            logger.info(f"Downloaded voice message to {temp_path}")

            # Transcribe the audio
            transcribed_text = await self.transcribe_voice_file(temp_path)

            return transcribed_text

        except Exception as e:
            logger.error(f"Failed to download/transcribe voice message: {e}")
            return None

        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug(f"Cleaned up temporary file: {temp_path}")
                except:
                    pass

# Global transcriber instance
transcriber = VoiceTranscriber()