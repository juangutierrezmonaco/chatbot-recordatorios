# 🚀 Deploy en Fly.io - Guía Paso a Paso

## 1. Instalar Fly CLI

**Linux/WSL:**
```bash
curl -L https://fly.io/install.sh | sh
```

**macOS:**
```bash
brew install flyctl
```

**Windows:**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

## 2. Crear cuenta y autenticarse

```bash
fly auth signup
# o si ya tenés cuenta:
fly auth login
```

## 3. Crear la app

```bash
# Desde la carpeta del proyecto
fly apps create chatbot-recordatorios
```

## 4. Crear el volumen para persistir datos

```bash
# Volumen único para todos los datos (base de datos, exports, galería)
fly volumes create chatbot_data --region scl --size 3
```

**Nota**: El plan gratuito solo permite 1 volumen, por eso agrupamos todo.

## 5. Configurar variables de entorno

```bash
# Token de Telegram (OBLIGATORIO)
fly secrets set TELEGRAM_TOKEN="tu_token_de_telegram_aqui"

# OpenAI API Key (OPCIONAL - solo para mensajes de voz)
fly secrets set OPENAI_API_KEY="tu_openai_key_aqui"
```

## 6. Deploy inicial

```bash
fly deploy
```

## 7. Ver logs y monitorear

```bash
# Ver logs en tiempo real
fly logs

# Ver estado de la app
fly status

# Abrir dashboard web
fly open
```

## 🔧 Comandos útiles

```bash
# Redeploy después de cambios
fly deploy

# Reiniciar la app
fly restart

# Ver máquinas/instancias
fly machines list

# Conectarse a la consola de la app
fly ssh console

# Ver métricas
fly metrics

# Escalar (si necesitás más recursos)
fly scale count 1
fly scale memory 512
```

## 🐛 Troubleshooting

**Error "no open ports":**
- No es problema para bots de Telegram, ignoralo

**Bot no responde:**
- Verificá logs: `fly logs`
- Verificá que el token esté bien: `fly secrets list`

**Base de datos se pierde:**
- Los volúmenes deben estar montados correctamente
- Verificá con: `fly volumes list`

**Memoria insuficiente:**
- Escalá: `fly scale memory 512`

## 💰 Límites del plan gratuito

- ✅ 3 apps gratis
- ✅ 160GB-hour/mes (suficiente para bot 24/7)
- ✅ 3GB de volúmenes persistentes
- ⚠️ Se pausa si no hay actividad por 1 semana

## 📝 Notas importantes

- La región `scl` (Santiago) está más cerca de Argentina
- Los volúmenes persisten tu base de datos y archivos
- Las variables de entorno se manejan con `fly secrets`
- El bot se mantiene corriendo 24/7 sin necesidad de webhooks