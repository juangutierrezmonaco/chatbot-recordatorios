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

---

## 🔄 Workflow de desarrollo y deploy

### **Después del deploy inicial, ¿cómo seguir?**

**✅ Workflow recomendado:**

1. **Hacer cambios localmente**
   ```bash
   # Editás tu código normalmente
   # Probás localmente con: python bot.py
   ```

2. **Commitear cambios**
   ```bash
   git add -A
   git commit -m "descripción de cambios"
   ```

3. **Pushear a GitHub** *(opcional pero recomendado)*
   ```bash
   git push origin master
   ```

4. **Deploy a Fly.io**
   ```bash
   fly deploy
   ```

### **¿Se actualiza automáticamente?**

❌ **No hay auto-deploy automático** como en Render
✅ **Tenés control total**: deployás cuando quieras

### **¿Puedo pushear tranquilo a GitHub?**

✅ **Sí, pushear a GitHub NO afecta Fly.io**
- GitHub y Fly.io son independientes
- Podés pushear cambios sin deployar
- Solo se actualiza cuando hacés `fly deploy`

### **¿Cuándo hacer deploy?**

🔹 **Después de probar localmente**
🔹 **Cuando quieras actualizar el bot en producción**
🔹 **NO hay límite de deploys** (plan gratuito)

### **Ejemplo de workflow típico:**

```bash
# 1. Hacer cambios
vim handlers.py

# 2. Probar localmente
python bot.py

# 3. Commitear
git add handlers.py
git commit -m "add new feature X"

# 4. (Opcional) Push a GitHub para backup
git push origin master

# 5. Deploy cuando estés listo
fly deploy

# 6. Monitorear logs
fly logs
```

### **⚡ Deploy rápido**

Si hacés cambios frecuentes y querés deployar rápido:

```bash
# Todo en una línea
git add -A && git commit -m "quick fix" && fly deploy
```

### **🚨 Si algo sale mal**

```bash
# Ver logs del deploy
fly logs

# Hacer rollback al deploy anterior
fly releases list
fly rollback <version_anterior>

# Reiniciar la app
fly restart
```