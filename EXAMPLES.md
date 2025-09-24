# 📖 Guía Completa de Ejemplos - Bot de Recordatorios

Esta guía contiene ejemplos detallados de todas las funcionalidades del bot de recordatorios.

## 🚀 Comandos Básicos

### /start
Muestra el mensaje de bienvenida con todas las opciones disponibles.

### Crear Recordatorios

#### Con comando /recordar
```
/recordar mañana 18:00 comprar comida
/recordar en 30m apagar el horno
/recordar 2025-09-25 15:30 reunión con Juan
/recordar el lunes 9:00 ir al gimnasio
/recordar pasado mañana 14:00 llamar al médico
```

#### Con lenguaje natural
```
Mañana a las 2 recordame que tengo turno médico
En 45 minutos recordame sacar la pizza del horno
El viernes a las 18hs haceme acordar de comprar cerveza
El lunes 29 a las 15 recordame entregar el informe
Recordame en una hora tomar la pastilla
```

### Ver Recordatorios

#### Listar todos los activos
```
/lista
```
Muestra todos los recordatorios pendientes ordenados por fecha.

#### Ver recordatorios de hoy
```
/hoy
```
Muestra todos los recordatorios del día actual, tanto pendientes como ya enviados. Los enviados aparecen con ✅ (enviado).

#### Ver recordatorios de la semana
```
/semana
/semana todos
```
**`/semana`** - Muestra solo los recordatorios **pendientes** de la semana actual (lunes a domingo) agrupados por día.

**`/semana todos`** - Muestra **todos** los recordatorios de la semana (pendientes y enviados).

#### Ver recordatorios de una fecha específica
```
/dia 25/09/2025
/dia mañana
/dia el lunes
/dia 15 (día 15 del mes actual)
```

### Buscar Recordatorios

#### Búsqueda por texto
```
/buscar médico
/buscar "reunión trabajo"
/buscar comida
```

#### Búsqueda por categoría
```
/buscar categoria:trabajo
/buscar categoría:salud
/buscar #compras
/buscar #personal
```

### Historial de Recordatorios
```
/historial
```
Muestra los últimos 20 recordatorios que ya se enviaron o fueron cancelados.

### Cancelar Recordatorios

#### Cancelar uno específico
```
/cancelar 5
```

#### Cancelar múltiples
```
/cancelar 1,2,3
/cancelar 1-5
/cancelar 1 2 3 4
/cancelar todos
```

## 🔥 Recordatorios Importantes (Con Repetición)

Los recordatorios importantes se repiten automáticamente cada X minutos hasta que los marques como completados.

### Crear Recordatorios Importantes

#### Con intervalo personalizado
```
/importante 10 mañana 9:00 ir al médico
```
✅ **Resultado:** Se repite cada 10 minutos desde las 9:00 hasta completar

```
/importante 5 en 2h llamar a Juan urgente
```
✅ **Resultado:** Se repite cada 5 minutos desde dentro de 2 horas

```
/importante 15 lunes 15:00 reunión con el jefe
```
✅ **Resultado:** Se repite cada 15 minutos desde el lunes a las 15:00

#### Con intervalo por defecto (5 minutos)
```
/importante mañana 8:00 tomar medicación
```
✅ **Resultado:** Se repite cada 5 minutos (intervalo por defecto)

```
/importante en 30m revisar el horno
```
✅ **Resultado:** Se repite cada 5 minutos desde dentro de 30 minutos

### Completar Recordatorios Importantes

#### Detener la repetición
```
/completar 123
```
✅ **Resultado:** El recordatorio #123 se marca como completado y **deja de repetirse**

### Notificaciones de Recordatorios Importantes

#### Formato especial
```
🔥 **RECORDATORIO IMPORTANTE** (#123):
tomar medicación

💡 Usa /completar 123 para detener la repetición.
```

#### En las listas aparecen así:
```
🔥 #123 - 25/09/2025 08:00 (cada 5min)
   tomar medicación
```

### Casos de Uso Recomendados

#### Medicación 💊
```
/importante 30 todos los días 8:00 tomar pastilla para la presión
/importante 60 lunes miércoles viernes 20:00 vitamina D
```

#### Trabajo urgente 💼
```
/importante 10 hoy 14:00 llamar al cliente que está esperando respuesta
/importante 15 mañana 9:00 enviar informe antes de la reunión
```

#### Eventos críticos ⚠️
```
/importante 5 en 45m sacar comida del horno
/importante 10 en 2h salir para el aeropuerto
```

### Límites y Restricciones

- **Intervalo mínimo:** 1 minuto
- **Intervalo máximo:** 60 minutos
- **Intervalo por defecto:** 5 minutos
- Solo se pueden completar con `/completar <id>`
- Sobreviven reinicios del bot
- Se diferencian visualmente con 🔥

## 📔 Sistema de Bitácora (Notas Permanentes)

### Crear Entradas en la Bitácora

#### Con comando /bitacora
```
/bitacora No me gustó el vino en Bar Central
/bitacora Si voy a La Parolaccia, pedir ravioles al pesto
/bitacora Pedro me recomendó el libro "Cien años de soledad"
```

#### Con lenguaje natural usando "Anotá"
```
Anotá me encanta el pan de tinto y barro
Anotá que el restaurante Don Julio tiene la mejor carne
Nota que María me debe $500
Apuntar que el mecánico de la esquina es muy bueno
```

### Ver Entradas de la Bitácora
```
/lista_bitacora
```
Muestra todas las entradas guardadas en la bitácora, ordenadas por fecha.

### Ver Entradas de la Bitácora
```
/listarBitacora
/lista_bitacora (compatible)
```
Muestra todas las entradas guardadas en la bitácora, ordenadas por fecha.

### Buscar en la Bitácora

#### Con comando tradicional
```
/buscarBitacora vino
/buscar_bitacora restaurante (compatible)
/buscarBitacora "pedro me"
```

#### Con comando "Averigua" (lenguaje natural)
```
Averigua vino
Averigua categoria:bares
Averigua #entretenimiento
```

#### Búsquedas conversacionales (preguntas)
```
¿Qué le gusta a Cindy?
¿Dónde come Pedro?
¿Cindy sugus?
¿Qué restaurante recomendó María?
```

#### Búsqueda por categoría
```
/buscarBitacora categoria:bares
/buscarBitacora #entretenimiento
/buscarBitacora categoría:lugares
```

### Eliminar de la Bitácora

#### Eliminar una entrada específica
```
/borrarBitacora 3
/borrar_bitacora 3 (compatible)
```
Elimina la entrada #3 de tu bitácora.

#### Eliminar todas las entradas
```
/borrarBitacora todos
```
Elimina todas las entradas activas de tu bitácora.

### Historial de la Bitácora
```
/historialBitacora
```
Muestra las últimas 20 entradas eliminadas de la bitácora con fechas de creación y eliminación.

## 🏷️ Sistema de Categorías

### Categorías Automáticas

El bot detecta automáticamente estas categorías basándose en palabras clave:

#### 💼 Trabajo
**Palabras clave:** trabajo, reunión, meeting, oficina, jefe, cliente, proyecto, presentación, deadline, entrega, equipo, empresa, negocio

**Ejemplos:**
```
Recordame mañana reunión con el cliente
/bitacora El proyecto X necesita más recursos
Anotá que Juan del equipo de ventas es muy eficiente
```

#### 🏥 Salud
**Palabras clave:** médico, doctor, dr., hospital, clínica, turno, consulta, medicina, pastilla, tratamiento, análisis, estudio, salud, dentista, odontólogo, psicólogo, terapia, farmacia, receta

**Ejemplos:**
```
/recordar lunes 9:00 turno con el médico
Recordame en 8 horas tomar la pastilla
/bitacora El Dr. García es muy recomendable
```

#### 👥 Personal
**Palabras clave:** cumpleaños, familia, mamá, papá, hermano, hermana, hijo, hija, esposo, esposa, novio, novia, amigo, personal, recomendó, recomienda, libro, sugiere, aconseja, le gusta, prefiere, le encanta

**Ejemplos:**
```
/recordar 15/10 cumpleaños de mamá
Mañana recordame llamar a Pedro
/bitacora A María le gustan las flores amarillas
```

#### 🛒 Compras
**Palabras clave:** comprar, supermercado, tienda, mercado, shopping, pagar, banco, farmacia, ferretería, verdulería

**Ejemplos:**
```
/recordar esta tarde comprar leche
Recordame ir al supermercado
/bitacora En el mercado central venden buen pescado
```

#### 🎬 Entretenimiento
**Palabras clave:** cine, película, teatro, concierto, partido, show, restaurante, bar, fiesta, vacaciones, viaje, música, banda, artista, baile, discoteca, pub, parrilla

**Ejemplos:**
```
/recordar viernes 20:00 ir al cine
Anotá que el bar La Madelón tiene buena música
/bitacora El restaurante Parolaccia tiene excelentes ravioles
```

#### 🏠 Hogar
**Palabras clave:** casa, hogar, limpieza, limpiar, cocinar, cocina, jardín, plantas, mascotas, perro, gato, reparar, arreglar, filtro, aire acondicionado, calefacción, electricidad, plomería, mantenimiento

**Ejemplos:**
```
/recordar sábado limpiar la casa
Recordame regar las plantas
/bitacora El plomero de la calle Corrientes es muy bueno
```

#### ⚙️ General
Se usa por defecto cuando no se detecta ninguna categoría específica.

### Categorías Explícitas

Puedes especificar manualmente la categoría usando la sintaxis `(categoría: nombre)` o `(categoria: nombre)`:

#### Para Recordatorios
```
/recordar mañana 15:00 entregar el trabajo práctico (categoría: facultad)
Recordame el miércoles devolver el libro (categoria: biblioteca)
Mañana a las 10 acordarme de la cita (categoría: citas)
```

#### Para la Bitácora
```
/bitacora Me gusta el pan de batata de BAUM (categoría: bares)
Anotá que el taller de la esquina es confiable (categoria: servicios)
/bitacora La farmacia del centro atiende hasta tarde (categoría: salud)
```

### Buscar por Categoría

#### Recordatorios por categoría
```
/buscar categoria:trabajo
/buscar categoría:salud
/buscar #compras
/buscar #personal
/buscar #facultad
```

#### Bitácora por categoría
```
/buscar_bitacora categoria:bares
/buscar_bitacora #entretenimiento
/buscar_bitacora categoría:servicios
/buscar_bitacora #lugares
```

## 🎙️ Mensajes de Voz

El bot puede transcribir mensajes de voz automáticamente (requiere API key de OpenAI):

### Para Recordatorios
```
🎤 "Recordame mañana a las 9 comprar leche"
🎤 "El viernes recordame llamar al dentista"
🎤 "En una hora acordarme de sacar la ropa del lavarropas"
```

### Para la Bitácora
```
🎤 "Anotá que no me gustó el restaurante La Parolaccia"
🎤 "Nota que Pedro me recomendó ver esa película"
🎤 "Recordar que María hace excelentes empanadas"
```

## 🔍 Búsquedas Avanzadas

### Búsqueda Sin Tildes y Parcial

El bot busca de forma inteligente, ignorando tildes y permitiendo coincidencias parciales:

#### Ejemplos de búsqueda sin tildes:
```
Buscar "medico" encuentra → "Turno con el médico"
Buscar "asi" encuentra → "Así me gusta"
Buscar "facil" encuentra → "Es muy fácil de usar"
```

#### Ejemplos de búsqueda parcial:
```
Buscar "facu" encuentra → "Entregar trabajo en la facultad"
Buscar "restau" encuentra → "El restaurante Don Carlos"
Buscar "cumple" encuentra → "Cumpleaños de María"
```

### Búsquedas Conversacionales

Puedes hacer preguntas naturales sobre tu bitácora:

#### Formatos de preguntas:
```
¿Qué le gusta a [persona]?
¿Dónde come [persona]?
¿Cómo es [cosa]?
¿Quién recomendó [lugar]?
[Persona] [tema]
```

#### Ejemplos reales:
```
Pregunta: "¿Qué le gusta a Cindy?"
Encuentra: "A Cindy le gustan los Sugus rosas y amarillos"

Pregunta: "¿Dónde come Pedro?"
Encuentra: "Pedro siempre va a La Parolaccia"

Pregunta: "Cindy sugus"
Encuentra: "A Cindy le gustan los Sugus rosas y amarillos"
```

#### Cómo funciona:
- Extrae palabras clave importantes de tu pregunta
- Busca en toda tu bitácora coincidencias
- Ordena resultados por relevancia (más coincidencias = mejor puntaje)
- Muestra los mejores 5 resultados con emojis 🎯 para alta relevancia

## 🔍 Funciones Avanzadas

### Fechas Inteligentes

El bot entiende múltiples formatos de fecha y hora:

#### Fechas Relativas
- `mañana`, `pasado mañana`
- `el lunes`, `el martes`, `el viernes`
- `la semana que viene`
- `el mes que viene`

#### Horas Inteligentes
- `a las 9` → 9:00 AM si es de mañana, 9:00 PM si es de noche
- `18:30` → formato 24 horas
- `6:30 PM` → formato 12 horas
- `en 30m`, `en 2 horas`

#### Fechas Específicas
- `25/09/2025`
- `el 15` (día 15 del mes actual)
- `lunes 29` (lunes más cercano que caiga día 29)

### Capitalización Automática

Todas las entradas se guardan con la primera letra en mayúscula:

```
Input:  "comprar pan"
Output: "Comprar pan"

Input:  "REUNIÓN CON JUAN"
Output: "REUNIÓN CON JUAN" (se mantiene si ya está en mayúsculas)
```

### Aislamiento por Usuario

Cada chat tiene sus propios datos completamente separados:
- Recordatorios independientes
- Bitácora independiente
- Búsquedas aisladas
- Historial separado

## 📊 Formato de Respuestas

### Recordatorios
```
✅ Dale, te aviso el 25/09/2025 15:30: "Reunión con cliente" [#trabajo] (ID #123)
```

### Bitácora
```
📖 Guardado en la bitácora (#45): "Me gusta el vino de esta bodega" [#bares]
```

### Listas
```
📋 Tus recordatorios activos:

🔔 #123 - 25/09/2025 15:30 [#trabajo]
   Reunión con cliente

🔔 #124 - 26/09/2025 09:00 [#salud]
   Turno con el médico
```

### Búsquedas
```
🔍 Recordatorios de categoría "trabajo":

🔔 #123 - 25/09/2025 15:30
   Reunión con cliente

🔔 #125 - 28/09/2025 14:00
   Entregar informe mensual
```

## 💡 Consejos y Trucos

### Para Mejores Resultados
1. **Especifica la hora:** `mañana 9:00` es mejor que solo `mañana`
2. **Usa categorías explícitas** para organizarte mejor: `(categoría: trabajo)`
3. **Aprovecha las búsquedas por categoría** para encontrar información relacionada
4. **Usa "Anotá"** para notas rápidas que no requieren fecha

### Palabras Clave Útiles
- **Recordatorios:** recordar, recordame, aviso, avisame, haceme acordar
- **Bitácora:** anotá, nota que, apuntar que, recordar que, guardar que
- **Búsquedas:** categoria:, categoría:, #categoria

### Gestión de Categorías
- Usa categorías consistentes para mejor organización
- Las categorías explícitas tienen prioridad sobre las automáticas
- Combina búsquedas por texto y categoría según necesites

## 🛠️ Configuración Técnica

### Variables de Entorno Requeridas
```bash
TELEGRAM_TOKEN=tu_token_de_telegram    # Obligatorio
OPENAI_API_KEY=tu_api_key_openai      # Opcional, para mensajes de voz
```

### Base de Datos
- SQLite con migraciones automáticas
- Tablas: users, reminders, vault, schema_migrations
- Índices optimizados para búsquedas por categoría
- Aislamiento completo por chat_id

### Sistema de Migraciones
El bot incluye un sistema robusto de migraciones que actualiza automáticamente la estructura de la base de datos al iniciar.

## 📄 Exportación de Datos a PDF

Puedes exportar todos tus datos (recordatorios y bitácora) a un documento PDF profesional.

### Comandos de Exportación

#### Exportación básica (solo datos activos)
```
/exportar
```
✅ **Incluye:**
- Recordatorios activos/pendientes
- Entradas de bitácora activas
- Resumen estadístico por categorías

#### Exportación completa (con historial)
```
/exportar completo
```
✅ **Incluye todo lo anterior más:**
- Recordatorios enviados y cancelados
- Entradas de bitácora eliminadas
- Historial completo de actividad

### Contenido del PDF

#### Secciones incluidas:
1. **Header del usuario** - Nombre, username, fecha de exportación
2. **Resumen estadístico** - Conteos por tipo y categoría
3. **Recordatorios** - Organizados por estado (pendientes/enviados/cancelados)
4. **Bitácora** - Agrupada por categoría con fechas

#### Formato de exportación:
```
📋 Exportación de Datos - Bot de Recordatorios

Usuario: Juan Pérez (@juangutierrez)
Chat ID: 123456789
Fecha de exportación: 23/09/2025 16:45:30
Zona horaria: America/Argentina/Buenos_Aires

📊 Resumen de Datos
┌─────────────────┬───────┬─────────┬─────────────────────┐
│ Tipo de Dato    │ Total │ Activos │ Completados/Elimin  │
├─────────────────┼───────┼─────────┼─────────────────────┤
│ Recordatorios   │   25  │    15   │          10         │
│ Bitácora        │   50  │    45   │           5         │
└─────────────────┴───────┴─────────┴─────────────────────┘

🔔 Recordatorios Pendientes
┌────┬──────────────┬───────────┬─────────────────────────┐
│ ID │  Fecha/Hora  │ Categoría │         Texto           │
├────┼──────────────┼───────────┼─────────────────────────┤
│123 │25/09/25 15:30│  Trabajo  │ Reunión con cliente     │
│124 │26/09/25 09:00│   Salud   │ Turno con el médico     │
└────┴──────────────┴───────────┴─────────────────────────┘

🔥 Recordatorios Importantes aparecen diferenciados
```

### Características del PDF

#### Formato profesional:
- ✅ **Texto completo** - Sin truncar contenido
- ✅ **Tablas dinámicas** - Se ajustan al contenido
- ✅ **Diferenciación visual** - Recordatorios importantes con 🔥
- ✅ **Organización clara** - Por secciones y categorías
- ✅ **Estadísticas** - Resumen cuantitativo de tu actividad

#### Nombre del archivo:
```
exportacion_datos_123456789_20250923_164530.pdf
```
Format: `exportacion_datos_{chat_id}_{timestamp}.pdf`

### Casos de Uso

#### Backup personal 💾
```
/exportar completo
```
Generas un respaldo completo de todos tus datos para archivo personal.

#### Reporte de actividad 📊
```
/exportar
```
Obtienes un resumen actual de tus recordatorios y notas activas.

#### Migración de datos 🔄
Si cambias de teléfono o chat, puedes exportar todo y tener un registro completo.

### Limitaciones

- **Generación bajo demanda** - No se guardan PDFs en el servidor
- **Archivo temporal** - Se elimina automáticamente después del envío
- **Tamaño de archivo** - Depende de la cantidad de datos (típicamente < 5MB)

## 🔄 Duplicación de Recordatorios

### Comando `/repetir`

#### Sintaxis
```
/repetir <id> [nueva fecha/hora]
```

#### Ejemplos Prácticos

**Repetir con nueva fecha:**
```
/repetir 123 mañana a las 10
```
✅ **Resultado:** Crea una copia del recordatorio #123 programada para mañana a las 10:00

**Repetir con fecha original:**
```
/repetir 456
```
✅ **Resultado:** Crea una copia exacta del recordatorio #456 con la misma fecha/hora

**Casos de uso típicos:**
```
# Reunión semanal
/repetir 789 el próximo martes a las 15:30

# Medicamento diario
/repetir 321 mañana a las 8

# Recordatorio mensual
/repetir 654 el 15 del próximo mes
```

## 📅 Comando `/dia` Mejorado

### Búsqueda de Fechas Pasadas

#### Nuevas Funcionalidades
```
/dia ayer          # Recordatorios de ayer
/dia 22/09         # 22 de septiembre (año actual)
/dia el lunes      # Último/próximo lunes
/dia 25/12/2023    # Fecha específica con año
```

#### Ejemplos Comparativos

**Antes (solo futuro):**
```
/dia 22/09
❌ Interpretaba como 22/09/2026 si 22/09/2025 ya pasó
```

**Ahora (inteligente):**
```
/dia 22/09
✅ Muestra 22/09/2025 (año actual), pasado o futuro
```

**Casos de uso:**
```
# Revisar qué hice ayer
/dia ayer

# Verificar recordatorios de fecha pasada
/dia 15/09

# Planificar día futuro
/dia mañana

# Revisar día específico
/dia el viernes
```

## 🎯 Sistema de Ayuda

### Comando `/explicar`

#### Ayuda Interactiva
```
/explicar recordar     # Guía completa del comando recordar
/explicar importante   # Cómo usar recordatorios importantes
/explicar lista       # Todas las opciones de listado
/explicar bitacora    # Sistema de notas personales
```

#### Ejemplo de Salida
```
/explicar recordar

📝 **Comando /recordar**

**Descripción:** Crea recordatorios con fechas y horarios flexibles

**Sintaxis:** `/recordar <fecha/hora> <texto>`

**Ejemplos:**
• `/recordar mañana a las 10 reunión con Juan`
• `/recordar el viernes a las 15:30 llamar al médico`
• `/recordar 25/12 a las 9 feliz navidad!`

**Características:**
🕐 Horarios inteligentes (AM/PM automático)
📅 Fechas flexibles (mañana, viernes, 25/12)
⚡ Fechas relativas (en 2 horas, pasado mañana)
🏷️ Categorización automática
🔔 Notificaciones puntuales
```

## 💡 Casos de Uso Recomendados

### Flujos de Trabajo Mejorados

#### Planificación Semanal
```
1. /semana                          # Ver toda la semana
2. /repetir 123 la próxima semana   # Duplicar tareas recurrentes
3. /explicar dia                    # Si necesitas ayuda con fechas
```

#### Seguimiento Diario
```
1. /hoy                             # Revisar día actual
2. /dia ayer                        # Ver qué se completó ayer
3. /dia mañana                      # Planificar día siguiente
```

#### Gestión de Recordatorios Recurrentes
```
1. /lista                           # Ver recordatorios activos
2. /repetir 456 la próxima semana   # Duplicar eventos semanales
3. /repetir 789 el próximo mes      # Duplicar eventos mensuales
```

### Mejores Prácticas Actualizadas
- **Usa categorías descriptivas** para mejor organización
- **Programa recordatorios importantes** para cosas críticas
- **Exporta regularmente** para hacer backup de tus datos
- **Usa fechas relativas** (`mañana`, `en 2 horas`) para flexibilidad
- **Duplica recordatorios recurrentes** con `/repetir` para ahorrar tiempo
- **Consulta fechas pasadas** con `/dia` para hacer seguimiento
- **Usa `/explicar`** cuando necesites recordar cómo funciona un comando

---

🤖 **Bot desarrollado con Claude Code** - Todas las funcionalidades están completamente integradas y probadas.