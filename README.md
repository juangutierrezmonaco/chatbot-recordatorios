# 🤖 Bot de Recordatorios para Telegram

Un bot de Telegram inteligente que te permite crear recordatorios usando comandos o lenguaje natural en español.

## 🚀 Deploy Gratis en Render (Recomendado)

**¡La forma más fácil de tener tu bot funcionando 24/7 gratis!**

1. **Fork este repositorio en tu GitHub**

2. **Ve a [render.com](https://render.com) y crea una cuenta**

3. **Conecta tu repositorio:**
   - Click en "New +" → "Web Service"
   - Conecta tu repo de GitHub
   - Render detectará automáticamente que es una app Python

4. **Configura las variables de entorno:**
   - `TELEGRAM_TOKEN`: Tu token de Telegram
   - `OPENAI_API_KEY`: (Opcional) Para mensajes de voz

5. **¡Deploy automático!** Render creará y ejecutará tu bot

**✅ Ventajas de Render:**
- 🆓 **Gratis**: 750 horas/mes (suficiente para 24/7)
- 🔄 **Auto-deploy**: Se actualiza con cada git push
- 📊 **Logs**: Para monitorear tu bot
- 💾 **SQLite**: Tu base de datos funciona sin cambios

---

## 🛠️ Instalación Local (Desarrollo)

1. **Clonar el repositorio:**
```bash
git clone <url-del-repo>
cd chatbot-recordatorios
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Configurar variables de entorno:**

Crear un archivo `.env` en la raíz del proyecto:
```
TELEGRAM_TOKEN=tu_token_aqui
OPENAI_API_KEY=tu_openai_api_key_aqui
```

4. **Ejecutar el bot:**
```bash
python3 bot.py
```

### 🔑 **Obtener Credenciales:**

**Token de Telegram:**
1. Habla con [@BotFather](https://t.me/botfather) en Telegram
2. Usa `/newbot` y sigue las instrucciones
3. Copia el token que te da

**OpenAI API Key (opcional):**
1. Ve a [platform.openai.com](https://platform.openai.com/)
2. Crea una cuenta y ve a API Keys
3. Genera una nueva API key
4. **Nota:** Para mensajes de voz (requiere créditos)

## 📋 Funcionalidades

### ✨ **Comandos Principales:**
- `/start` - Mensaje de bienvenida
- `/recordar <fecha/hora> <texto>` - Crear recordatorios
- `/lista [filtro]` - Ver recordatorios por categoría
- `/hoy` - Recordatorios de hoy (pendientes y enviados)
- `/semana [pendientes]` - Vista semanal completa
- `/dia <fecha>` - Ver cualquier día (incluye "ayer", fechas pasadas)
- `/buscar <término>` - Búsqueda inteligente
- `/historial [límite]` - Recordatorios pasados
- `/repetir <id> [nueva_fecha]` - Duplicar recordatorios
- `/cancelar <id>` - Cancelar recordatorio(s)
- `/importante <intervalo> <fecha> <texto>` - Recordatorios que se repiten
- `/completar <id>` - Completar recordatorios importantes
- `/exportar [completo]` - Exportar a PDF

### 📖 **Sistema de Bitácora:**
- `/bitacora <texto>` - Crear nota
- `/listarBitacora [límite]` - Ver todas las notas
- `/buscarBitacora <término>` - Buscar en notas
- `/borrarBitacora <id>` - Eliminar notas
- `/historialBitacora` - Historial completo

### 💕 **Funciones Especiales:**
- `/novia` - Modo romántico con validación
- `/fortuna` - Fortuna diaria romántica
- `/admin` - Modo administrador
- `/subirSorpresa` - Subir fotos (admin)
- `/sorpresa` - Recibir sorpresas aleatorias
- `/explicar <comando>` - Ayuda detallada

### 🌟 **Ejemplos de comandos:**

```
/recordar mañana 18:00 comprar comida
/recordar en una hora tomar medicamento
/repetir 14 en dos horas
/importante 15 hoy a las 21:00 tomar pastilla
/dia ayer
/semana pendientes
/exportar completo
```

### Lenguaje natural:

El bot también entiende frases libres en español:

```
Mañana a las 2 recordame que tengo turno médico
En 45 minutos recordame sacar la pizza
El viernes a las 18hs haceme acordar de comprar cerveza
El lunes 29 a las 15 recordame pedir el pedal
```

### Mensajes de voz: 🎙️

¡Envía mensajes de voz y el bot los transcribirá automáticamente!

**Ejemplos de mensajes de voz:**
- "Recordame mañana a las 9 comprar leche"
- "Nota que no me gustó el restaurante La Parolaccia"
- "El viernes recordame llamar al dentista"

**Configuración requerida:**
- Necesitas configurar `OPENAI_API_KEY` en tu archivo `.env`
- Requiere créditos en tu cuenta de OpenAI para funcionar

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