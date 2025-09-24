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

        # ========== RECORDATORIOS MODERNOS (reminders) ==========
        f.write("🔔 RECORDATORIOS MODERNOS\n")
        f.write("-" * 50 + "\n")

        try:
            cursor.execute("""
                SELECT id, chat_id, text, datetime, status, category,
                       is_important, repeat_interval, created_at, last_sent
                FROM reminders
                ORDER BY datetime DESC
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
                    f.write(f"Categoría: {reminder[5]}\n")
                    f.write(f"Importante: {'Sí' if reminder[6] else 'No'}\n")
                    if reminder[7]:
                        f.write(f"Intervalo repetición: {reminder[7]} min\n")
                    f.write(f"Creado: {reminder[8]}\n")
                    if reminder[9]:
                        f.write(f"Último envío: {reminder[9]}\n")
                    f.write("-" * 30 + "\n")

                f.write(f"\nTotal recordatorios modernos: {len(reminders)}\n")
            else:
                f.write("No hay recordatorios modernos.\n")
        except sqlite3.OperationalError as e:
            f.write(f"Error al leer recordatorios modernos: {e}\n")

        f.write("\n")

        # ========== RECORDATORIOS LEGACY (recordatorios) ==========
        f.write("🔔 RECORDATORIOS LEGACY\n")
        f.write("-" * 50 + "\n")

        try:
            cursor.execute("""
                SELECT id, chat_id, texto, fecha_hora, estado
                FROM recordatorios
                ORDER BY fecha_hora DESC
            """)

            legacy_reminders = cursor.fetchall()
            if legacy_reminders:
                for i, reminder in enumerate(legacy_reminders, 1):
                    f.write(f"#{i}\n")
                    f.write(f"ID: {reminder[0]}\n")
                    f.write(f"Chat ID: {reminder[1]}\n")
                    f.write(f"Texto: {reminder[2]}\n")
                    f.write(f"Fecha/Hora: {reminder[3]}\n")
                    f.write(f"Estado: {reminder[4]}\n")
                    f.write("-" * 30 + "\n")

                f.write(f"\nTotal recordatorios legacy: {len(legacy_reminders)}\n")
            else:
                f.write("No hay recordatorios legacy.\n")
        except sqlite3.OperationalError as e:
            f.write(f"Error al leer recordatorios legacy: {e}\n")

        f.write("\n")

        # ========== BITÁCORA (VAULT) ==========
        f.write("📖 BITÁCORA\n")
        f.write("-" * 50 + "\n")

        try:
            cursor.execute("""
                SELECT id, chat_id, text, category, created_at, status, deleted_at
                FROM vault
                ORDER BY created_at DESC
            """)

            vault_entries = cursor.fetchall()
            if vault_entries:
                for i, entry in enumerate(vault_entries, 1):
                    f.write(f"#{i}\n")
                    f.write(f"ID: {entry[0]}\n")
                    f.write(f"Chat ID: {entry[1]}\n")
                    f.write(f"Texto: {entry[2]}\n")
                    f.write(f"Categoría: {entry[3]}\n")
                    f.write(f"Creado: {entry[4]}\n")
                    f.write(f"Estado: {entry[5]}\n")
                    if entry[6]:
                        f.write(f"Eliminado: {entry[6]}\n")
                    f.write("-" * 30 + "\n")

                f.write(f"\nTotal notas bitácora: {len(vault_entries)}\n")
            else:
                f.write("No hay notas en la bitácora.\n")
        except sqlite3.OperationalError as e:
            f.write(f"Error al leer bitácora: {e}\n")

        f.write("\n")

        # ========== USUARIOS ==========
        f.write("👥 USUARIOS\n")
        f.write("-" * 50 + "\n")

        try:
            cursor.execute("""
                SELECT id, chat_id, username, first_name, last_name, is_bot,
                       language_code, created_at, last_activity, is_girlfriend,
                       girlfriend_activated_at, is_admin, admin_activated_at
                FROM users
                ORDER BY created_at DESC
            """)

            users = cursor.fetchall()
            if users:
                for i, user in enumerate(users, 1):
                    f.write(f"#{i}\n")
                    f.write(f"ID: {user[0]}\n")
                    f.write(f"Chat ID: {user[1]}\n")
                    f.write(f"Username: {user[2] or 'Sin username'}\n")
                    f.write(f"Nombre: {user[3] or 'Sin nombre'}\n")
                    f.write(f"Apellido: {user[4] or 'Sin apellido'}\n")
                    f.write(f"Es bot: {'Sí' if user[5] else 'No'}\n")
                    f.write(f"Idioma: {user[6] or 'No especificado'}\n")
                    f.write(f"Registrado: {user[7]}\n")
                    f.write(f"Última actividad: {user[8]}\n")
                    f.write(f"Modo novia: {'Sí' if user[9] else 'No'}\n")
                    if user[10]:
                        f.write(f"Novia activado: {user[10]}\n")
                    f.write(f"Admin: {'Sí' if user[11] else 'No'}\n")
                    if user[12]:
                        f.write(f"Admin activado: {user[12]}\n")
                    f.write("-" * 30 + "\n")

                f.write(f"\nTotal usuarios: {len(users)}\n")
            else:
                f.write("No hay usuarios registrados.\n")
        except sqlite3.OperationalError as e:
            f.write(f"Error al leer usuarios: {e}\n")

        f.write("\n")

        # ========== GALERÍA SECRETA ==========
        f.write("🎁 GALERÍA SECRETA\n")
        f.write("-" * 50 + "\n")

        try:
            cursor.execute("""
                SELECT id, file_id, file_type, original_filename, description,
                       uploaded_by, uploaded_at, is_active, local_file_path
                FROM secret_gallery
                ORDER BY uploaded_at DESC
            """)

            gallery = cursor.fetchall()
            if gallery:
                for i, item in enumerate(gallery, 1):
                    f.write(f"#{i}\n")
                    f.write(f"ID: {item[0]}\n")
                    f.write(f"File ID: {item[1] or 'N/A'}\n")
                    f.write(f"Tipo: {item[2]}\n")
                    f.write(f"Archivo original: {item[3] or 'Sin nombre'}\n")
                    f.write(f"Descripción: {item[4] or 'Sin descripción'}\n")
                    f.write(f"Subido por: {item[5]}\n")
                    f.write(f"Fecha: {item[6]}\n")
                    f.write(f"Activo: {'Sí' if item[7] else 'No'}\n")
                    f.write(f"Ruta local: {item[8] or 'N/A'}\n")
                    f.write("-" * 30 + "\n")

                f.write(f"\nTotal archivos galería: {len(gallery)}\n")
            else:
                f.write("No hay archivos en la galería secreta.\n")
        except sqlite3.OperationalError as e:
            f.write(f"Error al leer galería secreta: {e}\n")

        f.write("\n")

        # ========== ESTADÍSTICAS GENERALES ==========
        f.write("📊 ESTADÍSTICAS GENERALES\n")
        f.write("-" * 50 + "\n")

        try:
            # Recordatorios modernos por estado
            cursor.execute("SELECT status, COUNT(*) FROM reminders GROUP BY status")
            modern_status = cursor.fetchall()
            if modern_status:
                f.write("Recordatorios modernos por estado:\n")
                for status, count in modern_status:
                    f.write(f"  {status}: {count}\n")

            # Recordatorios legacy por estado
            cursor.execute("SELECT estado, COUNT(*) FROM recordatorios GROUP BY estado")
            legacy_status = cursor.fetchall()
            if legacy_status:
                f.write("\nRecordatorios legacy por estado:\n")
                for estado, count in legacy_status:
                    f.write(f"  {estado}: {count}\n")

            # Notas por categoría
            cursor.execute("SELECT category, COUNT(*) FROM vault GROUP BY category")
            vault_categories = cursor.fetchall()
            if vault_categories:
                f.write("\nNotas por categoría:\n")
                for category, count in vault_categories:
                    f.write(f"  {category}: {count}\n")

            # Contadores totales
            cursor.execute("SELECT COUNT(*) FROM reminders")
            modern_total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM recordatorios")
            legacy_total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM vault")
            vault_total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users")
            users_total = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM secret_gallery")
            gallery_total = cursor.fetchone()[0]

            f.write(f"\nTotales:\n")
            f.write(f"  Recordatorios modernos: {modern_total}\n")
            f.write(f"  Recordatorios legacy: {legacy_total}\n")
            f.write(f"  Notas bitácora: {vault_total}\n")
            f.write(f"  Usuarios: {users_total}\n")
            f.write(f"  Archivos galería: {gallery_total}\n")

        except sqlite3.OperationalError as e:
            f.write(f"Error al generar estadísticas: {e}\n")

        conn.close()

        f.write("\n" + "=" * 80 + "\n")
        f.write("FIN DE LA EXPORTACIÓN\n")
        f.write("=" * 80 + "\n")

    print(f"✅ Exportación completa guardada en: {output_file}")
    print(f"📄 Archivo de texto plano listo para usar")

if __name__ == "__main__":
    export_database_to_txt()