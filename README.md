# 🤖 Bot de Recordatorios para Telegram

Un bot de Telegram inteligente que te permite crear recordatorios usando comandos o lenguaje natural en español.

## 🚀 Instalación

1. **Clonar el repositorio:**
```bash
git clone <url-del-repo>
cd chatbot-recordatorios
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar el token de Telegram:**

Opción A - Usar archivo .env (recomendado):
```bash
# El archivo .env ya está creado con el token configurado
# Solo asegúrate de que esté presente en el directorio raíz
```

Opción B - Variable de entorno:
```bash
export TELEGRAM_TOKEN='tu_token_del_botfather'
```

4. **Ejecutar el bot:**
```bash
python3 bot.py
```

## 📋 Funcionalidades

### Comandos disponibles:

- `/start` - Mensaje de bienvenida con instrucciones
- `/recordar <fecha/hora> <texto>` - Crear recordatorio
- `/lista` - Ver todos los recordatorios activos
- `/cancelar <id>` - Cancelar un recordatorio por ID

### Ejemplos de comandos:

```
/recordar mañana 18:00 comprar comida
/recordar en 30m apagar el horno
/recordar 2025-09-20 09:30 reunión con Juan
```

### Lenguaje natural:

El bot también entiende frases libres en español:

```
Mañana a las 2 recordame que tengo turno médico
En 45 minutos recordame sacar la pizza
El viernes a las 18hs haceme acordar de comprar cerveza
El 20/09 a las 9:30 recordame la reunión
```

## 🛠️ Estructura del proyecto

```
chatbot-recordatorios/
├── bot.py           # Punto de entrada principal
├── handlers.py      # Lógica de comandos y parsing
├── scheduler.py     # Gestión de recordatorios programados
├── db.py           # Funciones de base de datos
├── requirements.txt # Dependencias
├── .env            # Variables de entorno (no se commitea)
├── .gitignore      # Archivos a ignorar por git
└── README.md       # Este archivo
```

## 💾 Base de datos

El bot usa SQLite para persistir los recordatorios. La base de datos (`recordatorios.db`) se crea automáticamente al ejecutar el bot por primera vez.

## 🕰️ Zona horaria

Configurado para Argentina (America/Argentina/Buenos_Aires). Puedes cambiar la zona horaria en los archivos `scheduler.py` y `handlers.py`.

## 🔧 Configuración avanzada

### Variables de entorno:

- `TELEGRAM_TOKEN` (requerida): Token del bot de Telegram

**📁 Archivo .env:**
El proyecto incluye un archivo `.env` con las variables configuradas. Este archivo contiene información sensible y está excluido del control de versiones por seguridad.

### Personalización:

- Modifica `DATEPARSER_SETTINGS` en `handlers.py` para cambiar idioma o formato de fechas
- Ajusta la zona horaria en `scheduler.py` y `handlers.py`
- Personaliza los mensajes en `handlers.py`

## 🐛 Troubleshooting

1. **Error "Token inválido"**: Verifica que `TELEGRAM_TOKEN` esté correctamente configurado
2. **Fechas no reconocidas**: El bot usa `dateparser` - asegúrate de usar formatos reconocibles
3. **Recordatorios no se envían**: Verifica que la fecha sea futura y el bot tenga permisos

## 📝 Logs

El bot genera logs detallados en la consola para debugging y monitoreo.