#!/usr/bin/env python3

import sqlite3
from datetime import datetime
import os

def export_database_to_txt():
    """Export complete database to simple TXT format."""

    db_path = 'recordatorios.db'
    if not os.path.exists(db_path):
        print("❌ No se encontró la base de datos recordatorios.db")
        return

    output_file = 'database_export.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("EXPORTACIÓN COMPLETA DE BASE DE DATOS\n")
        f.write(f"Fecha de exportación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Primero verificar qué tablas existen
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        f.write("📋 TABLAS ENCONTRADAS:\n")
        for table in tables:
            f.write(f"  - {table[0]}\n")
        f.write("\n")

        # ========== RECORDATORIOS ==========
        f.write("🔔 RECORDATORIOS\n")
        f.write("-" * 50 + "\n")

        try:
            cursor.execute("""
                SELECT id, chat_id, texto, fecha_hora, estado
                FROM recordatorios
                ORDER BY fecha_hora DESC
            """)

            reminders = cursor.fetchall()
            if reminders:
                for i, reminder in enumerate(reminders, 1):
                    f.write(f"#{i}\n")
                    f.write(f"ID: {reminder[0]}\n")
                    f.write(f"Chat ID: {reminder[1]}\n")
                    f.write(f"Texto: {reminder[2]}\n")
                    f.write(f"Fecha/Hora: {reminder[3]}\n")
                    f.write(f"Estado: {reminder[4]}\n")
                    f.write("-" * 30 + "\n")

                f.write(f"\nTotal recordatorios: {len(reminders)}\n")
            else:
                f.write("No hay recordatorios.\n")
        except sqlite3.OperationalError as e:
            f.write(f"Error al leer recordatorios: {e}\n")

        f.write("\n")

        # ========== ESTADÍSTICAS ==========
        f.write("📊 ESTADÍSTICAS\n")
        f.write("-" * 50 + "\n")

        try:
            # Contar recordatorios por estado
            cursor.execute("SELECT estado, COUNT(*) FROM recordatorios GROUP BY estado")
            status_counts = cursor.fetchall()
            if status_counts:
                f.write("Recordatorios por estado:\n")
                for status, count in status_counts:
                    f.write(f"  {status}: {count}\n")

            # Total de recordatorios
            cursor.execute("SELECT COUNT(*) FROM recordatorios")
            total_count = cursor.fetchone()[0]
            f.write(f"\nTotal de recordatorios: {total_count}\n")

            # Contar chats únicos
            cursor.execute("SELECT COUNT(DISTINCT chat_id) FROM recordatorios")
            chat_count = cursor.fetchone()[0]
            f.write(f"Chats únicos: {chat_count}\n")

        except sqlite3.OperationalError as e:
            f.write(f"Error al generar estadísticas: {e}\n")

        # ========== DATOS CRUDOS (COMPLETOS) ==========
        f.write("\n")
        f.write("🗃️ DATOS CRUDOS COMPLETOS\n")
        f.write("-" * 50 + "\n")

        try:
            cursor.execute("SELECT * FROM recordatorios ORDER BY id")
            all_data = cursor.fetchall()

            # Obtener nombres de columnas
            cursor.execute("PRAGMA table_info(recordatorios)")
            columns = [col[1] for col in cursor.fetchall()]

            f.write("Columnas: " + " | ".join(columns) + "\n")
            f.write("-" * 50 + "\n")

            for row in all_data:
                row_str = " | ".join(str(cell) for cell in row)
                f.write(f"{row_str}\n")

        except sqlite3.OperationalError as e:
            f.write(f"Error al exportar datos crudos: {e}\n")

        conn.close()

        f.write("\n" + "=" * 80 + "\n")
        f.write("FIN DE LA EXPORTACIÓN\n")
        f.write("=" * 80 + "\n")

    print(f"✅ Exportación completa guardada en: {output_file}")
    print(f"📄 Archivo de texto plano listo para usar")

if __name__ == "__main__":
    export_database_to_txt()