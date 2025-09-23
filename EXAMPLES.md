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
Muestra solo los recordatorios programados para el día actual.

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
/listar bitacora
/lista_bitacora (compatible)
```
Muestra todas las entradas guardadas en la bitácora, ordenadas por fecha.

### Buscar en la Bitácora

#### Con comando tradicional
```
/buscar bitacora vino
/buscar_bitacora restaurante (compatible)
/buscar bitacora "pedro me"
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
/buscar bitacora categoria:bares
/buscar bitacora #entretenimiento
/buscar bitacora categoría:lugares
```

### Eliminar de la Bitácora
```
/borrar bitacora 3
/borrar_bitacora 3 (compatible)
```
Elimina la entrada #3 de tu bitácora.

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
**Palabras clave:** médico, doctor, hospital, clínica, turno, consulta, medicina, pastilla, tratamiento, análisis, estudio, salud

**Ejemplos:**
```
/recordar lunes 9:00 turno con el médico
Recordame en 8 horas tomar la pastilla
/bitacora El Dr. García es muy recomendable
```

#### 👥 Personal
**Palabras clave:** cumpleaños, familia, mamá, papá, hermano, hermana, hijo, hija, esposo, esposa, novio, novia, amigo, personal

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
**Palabras clave:** cine, película, teatro, concierto, partido, show, restaurante, bar, fiesta, vacaciones, viaje

**Ejemplos:**
```
/recordar viernes 20:00 ir al cine
Anotá que el bar La Madelón tiene buena música
/bitacora El restaurante Parolaccia tiene excelentes ravioles
```

#### 🏠 Hogar
**Palabras clave:** casa, hogar, limpieza, limpiar, cocinar, cocina, jardín, plantas, mascotas, perro, gato, reparar, arreglar

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

---

🤖 **Bot desarrollado con Claude Code** - Todas las funcionalidades están completamente integradas y probadas.