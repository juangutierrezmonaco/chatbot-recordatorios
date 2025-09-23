# 📋 Documentación Técnica - Bot de Recordatorios

## 🚀 Descripción General

Este bot de Telegram permite a los usuarios crear recordatorios, mantener una bitácora personal, y gestionar tareas con un sistema robusto de categorización automática. Desarrollado en Python con SQLite como base de datos.

## 🛠️ Tecnologías Utilizadas

### Dependencias Principales
- **python-telegram-bot 20.8** - Framework para interactuar con la API de Telegram
- **APScheduler 3.10.4** - Programador de tareas para envío de recordatorios
- **SQLite3** (built-in) - Base de datos local para persistencia
- **dateparser 1.1.8** - Parsing inteligente de fechas en lenguaje natural
- **pytz 2023.3** - Manejo de zonas horarias (Argentina/Buenos_Aires)
- **python-dotenv 1.0.0** - Gestión de variables de entorno
- **openai 1.3.0** - Transcripción de mensajes de voz (opcional)

### Tecnologías de Soporte
- **unicodedata** (built-in) - Normalización de texto para búsquedas sin tildes
- **re** (built-in) - Expresiones regulares para parsing de comandos
- **collections.defaultdict** - Agrupación eficiente de datos

## 📁 Estructura del Proyecto

```
chatbot-recordatorios/
├── bot.py                 # Punto de entrada principal
├── handlers.py           # Manejadores de comandos y mensajes
├── db.py                 # Capa de acceso a datos
├── scheduler.py          # Gestión de recordatorios programados
├── transcription.py      # Transcripción de mensajes de voz
├── migrations.py         # Sistema de migraciones de BD
├── migrations/           # Archivos de migración SQL
│   ├── 1.sql            # Creación inicial de tablas
│   ├── 2.sql            # Tabla de usuarios
│   ├── 3.sql            # Sistema de categorías
│   └── 4.sql            # Sistema de historial para bitácora
├── reminders.db          # Base de datos SQLite
├── requirements.txt      # Dependencias Python
├── .env                  # Variables de entorno
└── README.md            # Documentación de usuario
```

## 🗄️ Arquitectura de Base de Datos

### Tabla: `reminders`
Almacena todos los recordatorios de usuarios.

```sql
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,           -- ID único del chat de Telegram
    text TEXT NOT NULL,                 -- Contenido del recordatorio
    datetime TEXT NOT NULL,             -- Fecha/hora en formato ISO
    status TEXT DEFAULT 'active',       -- 'active', 'sent', 'cancelled'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    category TEXT DEFAULT 'general'     -- Categoría automática o explícita
);
```

**Índices:**
- `idx_reminders_chat_id` - Búsqueda por usuario
- `idx_reminders_status` - Filtrado por estado
- `idx_reminders_category` - Búsqueda por categoría

### Tabla: `vault` (Bitácora)
Almacena notas permanentes de usuarios.

```sql
CREATE TABLE vault (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,           -- ID único del chat de Telegram
    text TEXT NOT NULL,                 -- Contenido de la nota
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    category TEXT DEFAULT 'general',    -- Categoría automática o explícita
    status TEXT DEFAULT 'active',       -- 'active', 'deleted'
    deleted_at TEXT                     -- Timestamp de eliminación (soft delete)
);
```

**Índices:**
- `idx_vault_chat_id` - Búsqueda por usuario
- `idx_vault_category` - Búsqueda por categoría
- `idx_vault_status` - Filtrado por estado

### Tabla: `users`
Gestión de usuarios y aislamiento de datos.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL UNIQUE,   -- ID único del chat de Telegram
    username TEXT,                     -- @username de Telegram
    first_name TEXT,                   -- Nombre del usuario
    last_name TEXT,                    -- Apellido del usuario
    is_bot INTEGER DEFAULT 0,          -- 0=humano, 1=bot
    language_code TEXT DEFAULT 'es',   -- Idioma preferido
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_activity TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Índices:**
- `idx_users_chat_id` - Búsqueda rápida por chat
- `idx_users_last_activity` - Análisis de actividad

### Tabla: `schema_migrations`
Control de versiones de la base de datos.

```sql
CREATE TABLE schema_migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL UNIQUE,   -- Número de migración
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## 🔐 Sistema de Aislamiento de Usuarios

### Chat ID como Identificador Único
Cada chat de Telegram tiene un `chat_id` único que funciona como:
- **Identificador principal** de usuario
- **Clave de aislamiento** entre usuarios
- **Scope de todas las operaciones** de base de datos

### Flujo de Identificación
1. **Usuario envía mensaje** → Telegram asigna `chat_id`
2. **Bot recibe update** → Extrae `update.effective_chat.id`
3. **Registro automático** → Se crea entrada en tabla `users`
4. **Todas las operaciones** → Filtradas por `chat_id`

### Garantías de Aislamiento
- ✅ Cada usuario solo ve SUS recordatorios
- ✅ Cada usuario solo ve SU bitácora
- ✅ Búsquedas limitadas al scope del usuario
- ✅ Historial independiente por usuario

## 📋 Flujo de Procesamiento de Comandos

### 1. Recepción de Mensaje
```python
# bot.py - Configuración de handlers
application.add_handler(CommandHandler("recordar", handlers.remind_command))
application.add_handler(MessageHandler(filters.TEXT, handlers.free_message))
```

### 2. Procesamiento en handlers.py
```python
async def free_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Registro/actualización automática del usuario
    register_or_update_user(update)

    # 2. Normalización del texto
    text = update.message.text.lower()

    # 3. Detección de intención
    if any(keyword in text for keyword in vault_keywords):
        # Procesar como entrada de bitácora
    elif any(keyword in text for keyword in keywords):
        # Procesar como recordatorio
    elif '?' in text and any(word in text for word in ['que', 'quien']):
        # Procesar como búsqueda conversacional
```

### 3. Extracción de Datos
```python
# Parsing de fecha/hora
datetime_obj, reminder_text = extract_date_and_text(text)

# Extracción de categoría explícita
reminder_text, explicit_category = extract_explicit_category(reminder_text)

# Categorización automática
category = explicit_category or extract_category_from_text(reminder_text)
```

### 4. Persistencia en Base de Datos
```python
# db.py - Todas las operaciones incluyen chat_id
def add_reminder(chat_id: int, text: str, datetime_obj: datetime, category: str):
    cursor.execute('''
        INSERT INTO reminders (chat_id, text, datetime, category)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, text, datetime_obj.isoformat(), category))
```

## ⚡ Sistema de Programación de Recordatorios

### Arquitectura del Scheduler
```python
# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Configuración de timezone
scheduler = AsyncIOScheduler(timezone=pytz.timezone('America/Argentina/Buenos_Aires'))

# Programación de recordatorio
def schedule_reminder(bot: Bot, chat_id: int, reminder_id: int, text: str, datetime_obj: datetime):
    job_id = f"reminder_{reminder_id}"
    scheduler.add_job(
        send_reminder,                  # Función a ejecutar
        trigger=DateTrigger(run_date=datetime_obj),
        args=[bot, chat_id, reminder_id, text],
        id=job_id
    )
```

### Flujo de Recordatorios
1. **Creación** → Guardado en BD + Programación en scheduler
2. **Reinicio del bot** → Recarga automática desde BD
3. **Envío** → Mensaje a usuario + Marcado como 'sent'
4. **Cancelación** → Eliminación del scheduler + Marcado como 'cancelled'

### Persistencia de Jobs
- **Al iniciar**: `load_pending_reminders()` recarga todos los jobs activos
- **Gestión de expirados**: Jobs pasados se marcan como 'sent' automáticamente
- **Tolerancia a fallos**: `misfire_grace_time=60` para recuperación

## 🔍 Sistema de Búsqueda Avanzada

### Normalización de Texto
```python
def normalize_text_for_search(text: str) -> str:
    # Elimina tildes y convierte a minúsculas
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents.lower()
```

### Tipos de Búsqueda

#### 1. Búsqueda Fuzzy (Tolerante)
```python
def search_vault_fuzzy(chat_id: int, keyword: str) -> List[Dict]:
    normalized_keyword = normalize_text_for_search(keyword)
    # Busca coincidencias parciales sin tildes
```

#### 2. Búsqueda Conversacional
```python
def search_vault_conversational(chat_id: int, search_terms: List[str]) -> List[Dict]:
    # Puntúa entradas por número de términos encontrados
    # Ordena por relevancia (score descendente)
```

#### 3. Búsqueda por Categoría
```python
def search_vault_by_category(chat_id: int, category: str) -> List[Dict]:
    # Filtrado directo por categoría exacta
```

## 🏷️ Sistema de Categorización Automática

### Detección por Palabras Clave
```python
def extract_category_from_text(text: str) -> str:
    text_lower = text.lower()

    # Categorías con sus palabras clave
    categories = {
        'trabajo': ['reunión', 'cliente', 'proyecto', 'oficina'],
        'salud': ['médico', 'doctor', 'hospital', 'medicina'],
        'personal': ['familia', 'amigo', 'cumpleaños', 'le gusta'],
        'compras': ['supermercado', 'comprar', 'banco'],
        'entretenimiento': ['cine', 'restaurante', 'bar', 'música'],
        'hogar': ['casa', 'limpieza', 'plantas', 'filtro']
    }
```

### Precedencia de Categorías
1. **Categoría explícita** → `(categoría: trabajo)`
2. **Detección automática** → Por palabras clave
3. **Categoría por defecto** → `general`

## 🎙️ Sistema de Transcripción de Voz

### Configuración Opcional
```python
# transcription.py
import openai

async def transcribe_voice_message(file_path: str) -> str:
    if not os.getenv('OPENAI_API_KEY'):
        return None  # Funcionalidad deshabilitada

    # Transcripción usando Whisper API
    with open(file_path, 'rb') as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
```

### Flujo de Procesamiento
1. **Descarga** del archivo de voz desde Telegram
2. **Transcripción** usando OpenAI Whisper
3. **Procesamiento** como mensaje de texto normal
4. **Limpieza** automática del archivo temporal

## 🔄 Sistema de Migraciones

### Gestión de Versiones
```python
# migrations.py
class MigrationManager:
    def run_migrations(self):
        current_version = self.get_current_version()
        migration_files = self.get_migration_files()

        for version, file_path in migration_files:
            if version > current_version:
                self.apply_migration(version, file_path)
```

### Estructura de Migraciones
```sql
-- migrations/3.sql
-- Migration 3: add_category_fields
-- Created: 2025-09-23T13:00:00.000000

ALTER TABLE reminders ADD COLUMN category TEXT DEFAULT 'general';
CREATE INDEX IF NOT EXISTS idx_reminders_category ON reminders(category);
```

### Aplicación Automática
- **Al iniciar el bot** → Verifica y aplica migraciones pendientes
- **Versionado incremental** → Solo aplica las que faltan
- **Rollback** → No implementado (solo forward migrations)

## 🚦 Manejo de Errores y Logging

### Configuración de Logging
```python
# bot.py
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
```

### Categorías de Errores
- **InvalidToken** → Token de Telegram inválido
- **Database errors** → Fallos de SQLite
- **Scheduler errors** → Problemas con jobs
- **Transcription errors** → Fallos de OpenAI API

### Estrategias de Recuperación
- **Restart automático** del scheduler
- **Reintento** en operaciones de BD
- **Graceful degradation** en transcripción de voz

## 🔒 Seguridad y Privacidad

### Protección de Datos
- **Aislamiento total** por chat_id
- **Sin logs de contenido** personal
- **Soft delete** para conservar referencias

### Variables de Entorno
```bash
# .env
TELEGRAM_TOKEN=bot_token_here
OPENAI_API_KEY=optional_openai_key
```

### Validaciones
- **Sanitización** de entrada de usuario
- **Escape** de caracteres especiales en SQL
- **Validación** de tipos de datos

## 📊 Optimizaciones de Rendimiento

### Índices de Base de Datos
- **Búsquedas por usuario** → `idx_*_chat_id`
- **Filtros por estado** → `idx_*_status`
- **Búsquedas por categoría** → `idx_*_category`

### Caching y Memoria
- **Connection pooling** → SQLite con conexiones cortas
- **Lazy loading** → Solo carga datos necesarios
- **Batch operations** → Para cancelaciones múltiples

### Escalabilidad
- **SQLite** → Adecuado para uso personal/pequeño
- **Migración futura** → PostgreSQL para múltiples instancias
- **Horizontal scaling** → Bot stateless, BD centralizada

## 🚀 Deployment y Configuración

### Requisitos del Sistema
- **Python 3.8+**
- **SQLite 3**
- **Conexión a internet** (API de Telegram)
- **Token de bot** de @BotFather

### Variables de Entorno
| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `TELEGRAM_TOKEN` | ✅ | Token del bot de Telegram |
| `OPENAI_API_KEY` | ❌ | Para transcripción de voz |

### Proceso de Inicio
1. **Carga de configuración** → `.env` y validaciones
2. **Inicialización de BD** → Migraciones automáticas
3. **Configuración del scheduler** → Zona horaria Argentina
4. **Carga de recordatorios** → Jobs pendientes desde BD
5. **Inicio del polling** → Conexión a Telegram

## 🔧 Mantenimiento y Monitoreo

### Logs Importantes
```bash
# Inicio exitoso
INFO - ✅ Database initialized
INFO - ✅ Scheduler initialized
INFO - 🚀 Bot started successfully

# Actividad normal
INFO - Reminder 123 scheduled for 2025-09-23 15:30:00
INFO - Vault entry 45 added for chat 12345
INFO - User registered: chat_id=67890
```

### Tareas de Mantenimiento
- **Backup de BD** → Copia regular de `reminders.db`
- **Limpieza de logs** → Rotación de archivos de log
- **Monitoreo de espacio** → Crecimiento de base de datos

## 📈 Métricas y Estadísticas

### Datos Disponibles
- **Usuarios activos** → `SELECT COUNT(DISTINCT chat_id) FROM users`
- **Recordatorios por categoría** → Agrupación por `category`
- **Uso de bitácora** → Entradas por usuario y período
- **Tasa de completion** → Ratio sent/cancelled

### Queries Útiles
```sql
-- Usuarios más activos
SELECT chat_id, COUNT(*) as total_reminders
FROM reminders
GROUP BY chat_id
ORDER BY total_reminders DESC;

-- Categorías más usadas
SELECT category, COUNT(*) as usage_count
FROM reminders
GROUP BY category
ORDER BY usage_count DESC;
```

---

📝 **Documentación creada con Claude Code** - Última actualización: 2025-09-23