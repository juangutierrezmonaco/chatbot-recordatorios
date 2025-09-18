import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = "recordatorios.db"

def init_db():
    """Inicializa la base de datos y crea las tablas necesarias."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recordatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            texto TEXT NOT NULL,
            fecha_hora TEXT NOT NULL,
            estado TEXT DEFAULT 'activo'
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada")

def agregar_recordatorio(chat_id: int, texto: str, fecha_hora: datetime) -> int:
    """Agrega un nuevo recordatorio a la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO recordatorios (chat_id, texto, fecha_hora, estado)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, texto, fecha_hora.isoformat(), 'activo'))

    recordatorio_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Recordatorio {recordatorio_id} agregado para chat {chat_id}")
    return recordatorio_id

def obtener_recordatorios_activos(chat_id: int) -> List[Dict]:
    """Obtiene todos los recordatorios activos de un chat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, texto, fecha_hora
        FROM recordatorios
        WHERE chat_id = ? AND estado = 'activo'
        ORDER BY fecha_hora
    ''', (chat_id,))

    rows = cursor.fetchall()
    conn.close()

    recordatorios = []
    for row in rows:
        recordatorios.append({
            'id': row[0],
            'texto': row[1],
            'fecha_hora': datetime.fromisoformat(row[2])
        })

    return recordatorios

def obtener_todos_recordatorios_activos() -> List[Dict]:
    """Obtiene todos los recordatorios activos de todos los chats."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, chat_id, texto, fecha_hora
        FROM recordatorios
        WHERE estado = 'activo'
    ''')

    rows = cursor.fetchall()
    conn.close()

    recordatorios = []
    for row in rows:
        recordatorios.append({
            'id': row[0],
            'chat_id': row[1],
            'texto': row[2],
            'fecha_hora': datetime.fromisoformat(row[3])
        })

    return recordatorios

def cancelar_recordatorio(chat_id: int, recordatorio_id: int) -> bool:
    """Cancela un recordatorio específico."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE recordatorios
        SET estado = 'cancelado'
        WHERE id = ? AND chat_id = ? AND estado = 'activo'
    ''', (recordatorio_id, chat_id))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()

    if affected_rows > 0:
        logger.info(f"Recordatorio {recordatorio_id} cancelado")
        return True
    else:
        logger.warning(f"No se pudo cancelar recordatorio {recordatorio_id}")
        return False

def marcar_recordatorio_enviado(recordatorio_id: int):
    """Marca un recordatorio como enviado."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE recordatorios
        SET estado = 'enviado'
        WHERE id = ?
    ''', (recordatorio_id,))

    conn.commit()
    conn.close()
    logger.info(f"Recordatorio {recordatorio_id} marcado como enviado")