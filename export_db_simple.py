#!/usr/bin/env python3

import sqlite3
from datetime import datetime
import os

def export_database_to_txt():
    """Export complete database to simple TXT format - only showing data that exists."""

    # Use different paths for development vs production
    if os.path.exists('/app/data'):  # Production in Fly.io
        db_path = "/app/data/reminders.db"
        exports_path = "/app/data/exports"
    else:  # Local development
        db_path = "database/reminders.db"
        exports_path = "exports"

    if not os.path.exists(db_path):
        print(f"❌ No se encontró la base de datos {db_path}")
        return

    # Create exports directory if it doesn't exist
    os.makedirs(exports_path, exist_ok=True)

    # Find next available number for export
    export_number = 1
    while os.path.exists(f'{exports_path}/{export_number}.txt'):
        export_number += 1

    output_file = f'{exports_path}/{export_number}.txt'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("EXPORTACIÓN COMPLETA DE BASE DE DATOS\n")
        f.write(f"Fecha de exportación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get all tables and their record counts
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()

        f.write("📋 RESUMEN DE TABLAS:\n")
        table_data = {}
        for table_name in tables:
            table = table_name[0]
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                table_data[table] = count
                f.write(f"  - {table}: {count} registros\n")
            except Exception as e:
                f.write(f"  - {table}: Error al contar - {e}\n")
        f.write("\n")

        # Only export tables that have data
        data_exported = False

        # ========== RECORDATORIOS LEGACY ==========
        if table_data.get('recordatorios', 0) > 0:
            f.write("🔔 RECORDATORIOS (TABLA LEGACY)\n")
            f.write("-" * 50 + "\n")

            cursor.execute("SELECT * FROM recordatorios ORDER BY fecha_hora DESC")
            records = cursor.fetchall()

            # Get column names
            cursor.execute("PRAGMA table_info(recordatorios)")
            columns = [col[1] for col in cursor.fetchall()]

            for i, record in enumerate(records, 1):
                f.write(f"RECORDATORIO #{i}:\n")
                for j, value in enumerate(record):
                    f.write(f"  {columns[j]}: {value}\n")
                f.write("-" * 30 + "\n")

            f.write(f"\nTotal: {len(records)} recordatorios\n\n")
            data_exported = True

        # ========== RECORDATORIOS MODERNOS ==========
        if table_data.get('reminders', 0) > 0:
            f.write("🔔 RECORDATORIOS MODERNOS\n")
            f.write("-" * 50 + "\n")

            cursor.execute("SELECT * FROM reminders ORDER BY datetime DESC")
            records = cursor.fetchall()

            cursor.execute("PRAGMA table_info(reminders)")
            columns = [col[1] for col in cursor.fetchall()]

            for i, record in enumerate(records, 1):
                f.write(f"RECORDATORIO MODERNO #{i}:\n")
                for j, value in enumerate(record):
                    f.write(f"  {columns[j]}: {value}\n")
                f.write("-" * 30 + "\n")

            f.write(f"\nTotal: {len(records)} recordatorios modernos\n\n")
            data_exported = True

        # ========== BITÁCORA/VAULT ==========
        if table_data.get('vault', 0) > 0:
            f.write("📖 BITÁCORA/NOTAS\n")
            f.write("-" * 50 + "\n")

            cursor.execute("SELECT * FROM vault ORDER BY created_at DESC")
            records = cursor.fetchall()

            cursor.execute("PRAGMA table_info(vault)")
            columns = [col[1] for col in cursor.fetchall()]

            for i, record in enumerate(records, 1):
                f.write(f"NOTA #{i}:\n")
                for j, value in enumerate(record):
                    f.write(f"  {columns[j]}: {value}\n")
                f.write("-" * 30 + "\n")

            f.write(f"\nTotal: {len(records)} notas\n\n")
            data_exported = True

        # ========== USUARIOS ==========
        if table_data.get('users', 0) > 0:
            f.write("👥 USUARIOS\n")
            f.write("-" * 50 + "\n")

            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            records = cursor.fetchall()

            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]

            for i, record in enumerate(records, 1):
                f.write(f"USUARIO #{i}:\n")
                for j, value in enumerate(record):
                    f.write(f"  {columns[j]}: {value}\n")
                f.write("-" * 30 + "\n")

            f.write(f"\nTotal: {len(records)} usuarios\n\n")
            data_exported = True

        # ========== GALERÍA SECRETA ==========
        if table_data.get('secret_gallery', 0) > 0:
            f.write("🎁 GALERÍA SECRETA\n")
            f.write("-" * 50 + "\n")

            cursor.execute("SELECT * FROM secret_gallery ORDER BY uploaded_at DESC")
            records = cursor.fetchall()

            cursor.execute("PRAGMA table_info(secret_gallery)")
            columns = [col[1] for col in cursor.fetchall()]

            for i, record in enumerate(records, 1):
                f.write(f"ARCHIVO #{i}:\n")
                for j, value in enumerate(record):
                    f.write(f"  {columns[j]}: {value}\n")
                f.write("-" * 30 + "\n")

            f.write(f"\nTotal: {len(records)} archivos\n\n")
            data_exported = True

        # ========== OTRAS TABLAS CON DATOS ==========
        for table_name, count in table_data.items():
            if count > 0 and table_name not in ['recordatorios', 'reminders', 'vault', 'users', 'secret_gallery', 'schema_migrations']:
                f.write(f"📊 TABLA: {table_name.upper()}\n")
                f.write("-" * 50 + "\n")

                try:
                    cursor.execute(f"SELECT * FROM {table_name}")
                    records = cursor.fetchall()

                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall()]

                    for i, record in enumerate(records, 1):
                        f.write(f"REGISTRO #{i}:\n")
                        for j, value in enumerate(record):
                            f.write(f"  {columns[j]}: {value}\n")
                        f.write("-" * 30 + "\n")

                    f.write(f"\nTotal: {len(records)} registros\n\n")
                    data_exported = True

                except Exception as e:
                    f.write(f"Error al leer tabla {table_name}: {e}\n\n")

        if not data_exported:
            f.write("❌ No se encontraron datos en ninguna tabla.\n\n")

        conn.close()

        f.write("=" * 80 + "\n")
        f.write("FIN DE LA EXPORTACIÓN\n")
        f.write("=" * 80 + "\n")

    print(f"✅ Exportación completa guardada en: {output_file}")
    print(f"📄 Solo se exportaron las tablas que contienen datos")

if __name__ == "__main__":
    export_database_to_txt()