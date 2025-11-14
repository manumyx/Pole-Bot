# 🎯 POLE BOT - DISEÑO DETALLADO DEL SISTEMA v1.0
## *"7 palabras, E S E N C I A"*
## ⚠️ **FASE DE DESARROLLO - NO PUBLICADO**

---

## 📋 Conceptos Clave

### ¿Qué es una Pole Válida?
Un mensaje que contenga **SOLO** la palabra "pole" (case insensitive, sin espacios extra).

**Ejemplos válidos:** 
- `pole`, `Pole`, `POLE`, `PoLe`, `pOlE`

**Ejemplos NO válidos:** 
- `pole!`, `pole mañanera`, `hola pole`, `p o l e`, `pole `, ` pole`

---

## 🏁 Tipos de Pole y Ventanas Horarias (v2.1)

### ⚡ Regla Fundamental: **TODOS PUEDEN GANAR CADA DÍA**

**Cada usuario** puede hacer su pole diario y mantener su racha. No hay límite de ganadores.

**Pero el orden importa:**
- **Primero** que escribe "pole" → Pole **Crítica** 💎 (multiplicador 2.0x)
- **Segundo** que escribe "pole" → Pole **Secundón** 🥈 (puntos base especiales: 11 pts)
- **Resto** → Pole Normal/Marranero según la hora

---

### A) Categoría por horario (puntos base)

La hora a la que cada usuario escribe "pole" determina sus puntos base:

1) **Pole Crítica** 💎 (SOLO el primero del día)
- Usuario: El primer "pole" del día
- Puntos base: **20 pts** (directo, sin multiplicadores)
- Cuenta para racha: ✅ Sí

2) **Pole Secundón** 🥈 (SOLO el segundo del día)
- Usuario: El segundo "pole" del día
- Puntos base: **11 pts** (fijo, sin importar la hora)
- Cuenta para racha: ✅ Sí

3) **Pole Normal** 🏁 (Tercero en adelante, antes de las 12:00)
- Ventana: **08:00–12:00**
- Puntos base: **10 pts**
- Cuenta para racha: ✅ Sí

4) **Pole Marranero** 🐷 (Después de las 12:00)
- Ventana: **≥ 12:00** (mediodía en adelante)
- Puntos base: **7 pts**
- Cuenta para racha: ✅ Sí
- Se trackea con contador propio en estadísticas

---

### B) Resumen de puntos base

| Posición | Nombre | Puntos Base |
|----------|--------|-------------|
| 1º | Crítica 💎 | **20 pts** |
| 2º | Secundón 🥈 | **11 pts** |
| 3º+ (08:00–12:00) | Normal 🏁 | **10 pts** |
| 3º+ (≥12:00) | Marranero 🐷 | **7 pts** |

**Nota:** El Secundón siempre vale 11 pts (sin importar si es antes o después de las 12h).

---

## ⚠️ Sistema de Penalties (Warnings Discretos)

## ⚠️ Sistema de Penalties (Warnings Discretos)

### Filosofía: 3 Strikes, You're Out (Temporalmente)

El bot NO banea. Solo **pausa tu participación** temporalmente. Esto es un juego, no una prisión.

### Sistema de Advertencias

#### Strike 1: Advertencia Suave 🟡
```
Situación: Escribes "pole" antes de las 12h por primera vez
Respuesta del bot: Reacción 🚫 en tu mensaje + DM privado
```
**DM que recibes:**
```
⚠️ Strike 1/3

gemelo que no son ni las 12 mira el reloj 😭

Strikes: 🟡⚪⚪
```

#### Strike 2: Advertencia Seria 🟠
```
Situación: Segunda infracción (cualquier tipo)
Respuesta: Reacción 🚫 + Mensaje público breve + DM
```
**Mensaje público:**
```
@Usuario twin 😭👩‍🦯 te regalo un segundo strike (2/3)
```

**DM:**
```
⚠️ Strike 2/3

tío que ya van 2 veces espabila un poco 🥀

Strikes: 🟡🟠⚪
Resets en: 7 días
```

#### Strike 3: Time-Out 🔴
```
Situación: Tercera infracción
Respuesta: Mensaje público + Suspensión temporal
```
**Mensaje público:**
```
@Usuario a tomar por culo un rato anda (3/3)

cuando estoy en una competencia de ser un empanao y mi oponente eres tu 👨‍🦯 
nos vemos en 24 horas chat
```

**Durante la suspensión:**
- No puedes participar en pole por 24h
- Tus mensajes de "pole" son ignorados (sin reacción)
- Tu racha se CONGELA (no la pierdes aún)

### Tipos de Infracciones

1. **Pole Anticipada** (antes de las 12h) → Strike
2. **Spam de Pole** (escribir "pole" 3+ veces en 1 minuto) → Strike directo
3. **Intento durante suspensión** → +12h de suspensión adicional

### Sistema de Rehabilitación 🔄

- **Strikes reset:** Cada 7 días sin infracciones, -1 strike
- **Suspensión cumplida:** Vuelves con strikes intactos (para no abusar)
- **Mes limpio:** Borrado total del historial de strikes

### Penalties Manuales (Admin)

Los admins pueden:
- `!warn @user <razón>` - Dar un strike manual
- `!timeout @user <horas>` - Suspensión temporal custom
- `!forgive @user` - Perdonar strikes

---

## 📊 Sistema de Puntos (v1.0)

### Fórmula de puntuación

Puntos del día = `PuntosBase(posición)` × `MultiplicadorRacha`

- `PuntosBase(posición)` = 20 (Crítica 1º) | 11 (Secundón 2º) | 10 (Normal 3º+) | 7 (Marranero ≥12:00)
- `MultiplicadorRacha` = progresivo (ver abajo), con tope global **2.5x**

Notas:
- Los puntos base ya están definidos según tu posición (no hay multiplicador crítico separado).
- La racha multiplica el total.
- Opcional: bonus de precisión (12:00:00 ± 1s) se puede añadir más adelante si quieres.

#### Precisión y decimales
- El multiplicador de racha se aplica SOLO al premio del día (no al total acumulado).
- Con bases `20/11/10/7` y escalones de `+0.1x`, los casos de `11` y `7` pueden producir decimales (ej. `11 × 1.2 = 13.2`).
- No se realizan redondeos: se guarda y muestra el valor exacto resultante.

### Escala de Puntos (Normalización Entera - PENDIENTE DE ELECCIÓN)
Para evitar decimales y asegurar igualdad visual, se proponen dos enfoques. Se decidirá antes de la implementación final.

| Opción | Descripción | Bases | Ejemplo con racha 1.7x (según hitos) | Ventajas | Inconvenientes |
|--------|-------------|-------|--------------------------------------|----------|----------------|
| A (Mantener + decimales) | Actual, sin cambios | 20 / 11 / 10 / 7 | Crítica 20×1.7 = 34 | Simplicidad | Decimales en Secundón/Marranero |
| B (Escala ×10) | Multiplicar todas las bases por 10 | 200 / 110 / 100 / 70 | Crítica 200×1.7 = 340 | Evita decimales, números moderados | Requiere migración / mostrar formato |
| C (Escala ×100) | Multiplicar todas las bases por 100 | 2000 / 1100 / 1000 / 700 | Crítica 2000×1.7 = 3400 | Total integridad + precisión futura | Números grandes, posible ruido visual |

Implementación recomendada: **Opción B (×10)** para mantener legibilidad y eliminar decimales (todas las bases son múltiplos de 10, escalones 0.1x siempre generan enteros). Si eliges esta opción se adaptará todo el documento y las notificaciones (ej: Crítica pasa de 20 a 200).

Formato visual si se adopta escala:
- Almacenar internamente entero (ej: 340) y mostrar dividido por 10 si se desea continuar mostrando escala clásica (34). O mostrar directamente la versión escalada si buscamos impacto.
- Leaderboards pueden tener toggle: "Vista Compacta" (34) / "Vista Precisa" (340).

Confirma opción para proceder con ajuste integral.

### Ejemplos Prácticos

**Escenario 1: Usuario1 gana Crítica**
```
[11:30:05] Usuario1: pole   ← Primero del día
Bot: 💎 ¡POLE CRÍTICA! 💎
Cálculo: 20 (Crítica) × 1.4 (Racha) = 28 pts
```

**Escenario 2: Usuario2 gana Secundón**
```
[11:30:05] Usuario1: pole   ← Primero (Crítica)
[11:30:08] Usuario2: pole   ← Segundo
Bot: 🥈 ¡SECUNDÓN! 
Cálculo: 11 (Secundón) × 1.2 (Racha) = 13.2 pts
```

**Escenario 3: Usuario3 hace pole Normal**
```
[11:30:05] Usuario1: pole   ← Crítica
[11:30:08] Usuario2: pole   ← Secundón
[11:45:00] Usuario3: pole   ← Normal (antes 12h)
Bot: 🏁 ¡POLE!
Cálculo: 10 (Normal) × 1.1 (Racha) = 11 pts
```

**Escenario 4: Usuario4 hace pole Marranero (tarde)**
```
[11:30:05] Usuario1: pole   ← Crítica
[11:30:08] Usuario2: pole   ← Secundón
[11:45:00] Usuario3: pole   ← Normal
[13:20:00] Usuario4: pole   ← Marranero (≥12h)
Bot: 🐷 Pole Marranero!
Cálculo: 7 (Marranero) × 1.0 (sin racha) = 7 pts
```

**Escenario 5: Todos mantienen su racha**
```
Día 1:
- Usuario1 → Crítica (20 pts) → Racha: 1 día ✅
- Usuario2 → Secundón (11 pts) → Racha: 1 día ✅
- Usuario3 → Normal (10 pts) → Racha: 1 día ✅
- Usuario4 → Marranero (7 pts) → Racha: 1 día ✅

Día 2 (todos repiten):
- Rachas aumentan a 2 días ✅
```

### Protección Anti-Lose/Lose

**Si pierdes tu racha:**
- 🛡️ **Conservas el 20% de los puntos de racha** acumulados
- 📈 Tu "Mejor Racha" queda registrada para siempre
- 🎯 Bonus de "Comeback": Primeras 3 poles después de perder racha = +5 pts extra

**Ejemplo:**
```
Tenías racha de 50 días (50 pts extra por pole)
Pierdes la racha :(

Conservas: 10 pts de "Experiencia de Racha"
Tus próximas 3 poles: Base + 5 pts de comeback
Tu mejor racha registrada: 50 días (para presumir)
```

### Cómo se Pierden Puntos

| Acción | Penalización |
|--------|--------------|
| Strike 1 | -0 pts (solo advertencia) |
| Strike 2 | -5 pts |
| Strike 3 | -10 pts + suspensión |
| Spam severo | -25 pts |

**Protección:** Nunca puedes bajar de 0 puntos (no hay puntos negativos).

---

## 🔥 Sistema de Rachas (Máx. 365 Días, tope 2.5x)

### Funcionamiento
```
Día 1: Haces pole → Racha: 1 día ✅
Día 2: Haces pole → Racha: 2 días ✅
Día 3: NO haces pole → ⚠️ RACHA PERDIDA (pero conservas 20% del valor)
Día 4: Haces pole → Racha: 1 día + Comeback Bonus
```

### Multiplicador de Racha (Sistema de Hitos)

Objetivo: llegar a un máximo de **2.5x** distribuido progresivamente hasta 365 días.

**Sistema de Hitos (Opción B adaptada):**

| Días | Multiplicador | Incremento |
|------|---------------|------------|
| 1-6 | 1.0x | Base |
| 7 | 1.1x | +0.1x |
| 14 | 1.2x | +0.1x |
| 21 | 1.3x | +0.1x |
| 30 | 1.4x | +0.1x |
| 45 | 1.5x | +0.1x |
| 60 | 1.6x | +0.1x |
| 75 | 1.7x | +0.1x |
| 90 | 1.8x | +0.1x |
| 120 | 1.9x | +0.1x |
| 150 | 2.0x | +0.1x |
| 180 | 2.1x | +0.1x |
| 210 | 2.2x | +0.1x |
| 240 | 2.3x | +0.1x |
| 270 | 2.4x | +0.1x |
| 300 | 2.5x | +0.1x (MÁXIMO) |
| 365 | 2.5x | Mantiene máximo |

Además de la multiplicación, mantenemos milestones cosméticos/recompensas:

| Días | Nombre | Emoji |
|------|--------|-------|
| 7 | Semana Perfecta | 🔥🔥 |
| 30 | Mes Legendario | 🔥🔥🔥 |
| 100 | Centurión | 👑 |
| 180 | Medio Año | 🌟 |
| 365 | Año Perfecto | 💎👑💎 |

### Tope Máximo: 365 Días

Después de 365 días consecutivos:
- 🏆 Obtienes el título **"Inmortal del Pole"**
- 💎 Badge permanente único
- 🔄 Tu racha se "gradúa" y empieza de nuevo
- 📊 Mantienes el récord en tu perfil para siempre

**¿Por qué 365 días?** Para que sea un logro ÉPICO pero alcanzable. Y para que no haya personas con rachas de 10 años que nadie puede alcanzar.

---

## 🎖️ Sistema de Rangos (Con Emojis Personalizados)

### ¿Cómo Funciona?

Tu **rango** aparece automáticamente junto a tu nombre en estadísticas y leaderboards.

**Basado en:** Puntos totales + Poles críticas + Mejor racha

### Tabla de Rangos

| Rango | Requisitos | Emoji del Bot | Descripción |
|-------|-----------|---------------|-------------|
| **Novato** | 0-49 pts | 🌱 | Estás empezando, todos fuimos novatos |
| **Aprendiz** | 50-199 pts | 🏃 | Ya le vas pillando el truco |
| **Competidor** | 200-499 pts | ⚔️ | Empiezas a dar miedo |
| **Veterano** | 500-999 pts | 🛡️ | Sabes lo que haces |
| **Experto** | 1000-1999 pts | 💪 | Un rival digno |
| **Maestro** | 2000-3999 pts | 🎯 | Entre los mejores |
| **Leyenda** | 4000-7999 pts | 👑 | Un nombre respetado |
| **Mito** | 8000-14999 pts | 🌟 | Historias se cuentan de ti |
| **Inmortal** | 15000+ pts | 💎 | Has trascendido |
| **Campeón Global** | Top 10 Global | 🏆 | Eres de los mejores del mundo |

### Títulos Especiales (Adicionales)

Estos se muestran JUNTO a tu rango:

- 💀 **"El Exterminador"** - 100+ poles críticas
- 🔥 **"Racha Infinita"** - Racha actual de 100+ días
- ⚡ **"Rayo"** - 50+ poles en primeros 5 segundos
- 🎯 **"Perfeccionista"** - 10+ poles a las 12:00:00 exactas
- 🛡️ **"Defensor"** - Ganaste 30 días en tu servidor favorito
- 👹 **"Cazador de Récords"** - Has roto 20+ récords personales

### Ejemplo Visual

```
📊 Perfil de Usuario

👤 @DarkPhoenix
🎖️ Rango: 💪 Experto | 💀 El Exterminador
📈 Puntos: 1,450
🏁 Poles: 87 (45 críticas)
🔥 Racha actual: 23 días
🏆 Mejor racha: 67 días
🌍 Representa a: Servidor "Los Insomnes"
```

---

## 🌍 Sistema de Zonas Horarias

### Configuración por Servidor
```
/settimezone Europe/Madrid
/settimezone America/New_York
/settimezone Asia/Tokyo
```

### Funcionamiento
- Cada servidor tiene su propia zona horaria
- El reset de pole se adapta a las 12h de ESA zona
- Los usuarios ven timestamps en la zona del servidor (por defecto)

### Zona Horaria Personal (Opcional)
```
/mytimezone America/Los_Angeles
```
- El bot te muestra las horas en TU zona horaria personal
- Pero el reset sigue siendo según el servidor
- Útil para usuarios en diferentes países

**Ejemplo:**
```
Servidor configurado en: Europe/Madrid (UTC+1)
Tu timezone personal: America/New_York (UTC-5)

Bot te muestra:
"🏁 Pole disponible en: 6:00 AM (tu hora local)"
Pero el reset real del servidor es a las 12:00 PM Madrid
```

---

## 🔔 Sistema de Notificaciones (Con Personalidad)

### Notificación de Reset (A las 12:00h)

**Versión estándar:**
```
🏁 POLE ABIERTO

son las 12:00 chat
a ver quién es el más rápido hoy

@RolePole (si está configurado)
```

**Versión con humor (aleatorio):**
```
⏰ DESPERTAD

12:00 en punto
el pole está ahí esperando

@RolePole
```

```
🔥 A CORRER

12:00 hermano
el que pestañea pierde

@RolePole
```

```
👀 YA ES LA HORA

12:00 bebés
preparad los dedos

@RolePole
```

### Notificación de Victoria

**Pole Crítica:**
```
💎 POLE CRÍTICA

@Usuario primer mensaje del día tío felicidades
⏱️ 12:00:03

💰 +20 pts | 🔥 racha: 12 días
🎯 total: 28 pts (con multiplicador)

imparable 🔥
```

**Pole Secundón:**
```
🥈 SECUNDÓN

@Usuario segundo del día
⏱️ 12:00:08

💰 +11 pts | 🔥 racha: 5 días
🎯 total: 13.2 pts

bien jugado 👏
```

**Pole Normal:**
```
🏁 POLE

@Usuario
⏱️ 12:05:30

💰 +10 pts | 🔥 racha: 5 días
🎯 total: 11 pts

así se hace 🤝
```

**Pole Marranero:**
```
🐷 POLE MARRANERO

@Usuario llegaste tarde hermano
⏱️ 13:20:00

💰 +7 pts
🎯 total: 7 pts

mañana madruga más 🥱
```

**Pole Perfecta (12:00:00):**
```
🤯 @Usuario

ESPERA ESPERA
12:00:00 EXACTAS???

hermano eso es ARTE
+[X] pts + bonus perfección

LEYENDA 👑
```

¡ESTO ES LEYENDA! 🏆
```

### Configuración de Notificaciones
```
/notify reset on/off          # Avisar cuando se abre pole
/notify winner on/off         # Avisar cuando alguien gana
/notify mention @role         # Mencionar rol específico
```

#### Ping Configurable del Reset (v1.0)
Soporte para elegir qué mencionar cuando se anuncia el pole abierto.

Modos:
- `none` → No se menciona ningún rol.
- `role:<id>` → Se menciona un rol concreto configurado por admin.
- `everyone` → Se permite @everyone pero requiere confirmación para activarlo.

Comando propuesto:
```
/poleping set <@rol|everyone|none>
/poleping show
```
Flujo especial @everyone:
1. Admin ejecuta `set everyone`.
2. Bot responde con advertencia: "⚠️ Usar @everyone puede generar spam. Confirma con /poleping confirm en 60s".
3. Admin ejecuta `/poleping confirm`.
4. Se guarda configuración.
5. Expira confirmación si no se ejecuta a tiempo.

Al guardar se persiste:
```
ping_mode: none|role|everyone
ping_role_id: <snowflake or null>
```
Panel `/config`: botón "Editar Ping" abre selector de rol + toggle @everyone.

---

## 📱 Comandos (Slash Commands Modernos)

### Comandos de Usuario

```
/pole                         # Info sobre el pole actual
/stats [@usuario]             # Tus stats o las de otro
/leaderboard [global/local]   # Ver ranking (con botones interactivos)
/streak                       # Ver tu racha
/achievements                 # Ver tus logros
/profile [@usuario]           # Ver perfil completo
/represent <servidor>         # Elegir servidor para ranking global
/mytimezone <zona>            # Tu zona horaria personal
```

### Comandos de Admin

```
/setpolechannel              # Configurar canal de pole
/settimezone <zona>          # Zona del servidor
/notify <opciones>           # Configurar notificaciones
/warn @usuario <razón>       # Dar strike manual
/forgive @usuario            # Perdonar strikes
/timeout @usuario <horas>    # Suspensión temporal
/config                      # Abrir panel de configuración
/enableglobal <yes/no>       # Participar en ranking global
```

### Comandos de Información

```
/help                        # Ayuda general
/rules                       # Reglas del pole
/info                        # Info del sistema
```

---

## 🎮 /leaderboard - Sistema Interactivo

### Vista Local (Servidor)

```
🏆 LEADERBOARD - Los Insomnes 🏆

1. 💪 @DarkPhoenix        1,450 pts | 🔥 23 días
2. ⚔️ @SpeedRunner        890 pts  | 🔥 8 días
3. 🛡️ @NightOwl           720 pts  | 🔥 15 días
4. 🏃 @QuickFingers       580 pts  | 🔥 3 días
5. ⚔️ @PoleHunter         510 pts  | 🔥 1 día

[Botón: 🌍 Ver Global] [Botón: 📊 Filtros]
```

### Vista Global

```
🌍 LEADERBOARD GLOBAL 🌍

1. 💎 @LegendaryUser     15,340 pts | 🌟 Servidor: Elite Gaming
2. 💎 @PoleGod          14,120 pts | 🌟 Servidor: Night Crew
3. 👑 @FastFingers      12,890 pts | 🌟 Servidor: Speed Demons
4. 💪 @DarkPhoenix       8,450 pts | 🌟 Servidor: Los Insomnes
5. 💪 @ChampionPole      7,920 pts | 🌟 Servidor: Pro Polers

[Botón: 🏠 Ver Local] [Botón: 🎯 Ver tu Posición]

Representas a: Los Insomnes
Tu posición global: #47 de 2,341
```

---

## ⚙️ /config - Panel de Configuración Interactivo

```
⚙️ CONFIGURACIÓN DEL SERVIDOR ⚙️

📍 Canal de Pole: #pole-diario
🌍 Zona Horaria: Europe/Madrid (UTC+1)
⏰ Hora de Reset: 12:00

🔔 Notificaciones:
  └─ Reset: ✅ Activado (@Polers)
  └─ Victoria: ✅ Activado
  └─ Rachas perdidas: ❌ Desactivado

🌐 Ranking Global: ✅ Participando
📊 Privacidad: Público

[Botón: ✏️ Editar Canal]
[Botón: 🌍 Cambiar Timezone]
[Botón: 🔔 Notificaciones]
[Botón: 🌐 Configurar Global]
```

---

## 💬 Personalidad del Bot (ESENCIA)

### Tono General
El bot habla como un colega que te echa la bulla pero nunca se pasa. Directo, sin cursilerías, con humor natural y emojis que dicen algo de verdad.

**Reglas de oro:**
- Nada de "¡Felicidades campeón!" genérico → mejor "tío te has lucido 🔥"
- Nada de sermones → si la cagas, te lo dice claro pero sin drama
- Emojis con sentido → no spam, solo los que refuerzan el mensaje
- Humor sin forzar → si no sale natural, mejor directo al grano

### Ejemplos de Respuestas con Humor

**Cuando alguien llega tarde:**
```
😴 @Usuario bro que son las 3 de la tarde
   @Winner ganó hace 3 horas ya te vale
   espabila un poco
```

```
🥸 @Usuario casi cuela
   @Winner te ha pasado por encima
   ponte las pilas gemelo
```

**Cuando alguien hace pole perfecta (12:00:00 exactas):**
```
🤯 @Usuario espera espera

12:00:00 EXACTAS???
hermano eso no es suerte es arte

+[X] puntos y mi respeto eterno 🫡
```

**Cuando alguien rompe su récord personal:**
```
🎉 @Usuario nuevo récord personal

antes: 45 días de racha
ahora: 46 días

así se hace tío sigue así 🔥
```

**Cuando alguien pierde una racha larga:**
```
💔 @Usuario

se acabó tu racha de 67 días hermano
duele lo sé pero conservas el 20% (13 pts)

67 días es una barbaridad tío
descansa y vuelve más fuerte 💪
```

**Cuando hay empate técnico (diferencia <0.1s):**
```
⚡ foto finish entre @Usuario1 y @Usuario2

diferencia: 0.03 segundos
ganador: @Usuario1

@Usuario2 tío estuviste a NADA
la próxima es tuya 🤝
```

**Easter Eggs (Mensajes Especiales Random):**

```
# Si es viernes
🎉 VIERNES BABY

hoy el pole vale el doble
porque sí porque me da la gana

que tengáis buen finde chat 🔥
```

```
# Si alguien gana 10 días seguidos
🔥 @Usuario lleva 10 días seguidos ganando

esto ya es personal tío
quien lo tumbe mañana se lleva +15 puntos bonus

a por él chat 😈
```

```
# Si nadie ha ganado en 5 minutos
⏰ hermano ya pasaron 5 minutos

¿nadie quiere el pole o qué?
está ahí tirado esperando 💀
```

```
# Si alguien intenta hacer pole a las 11:59
🤨 @Usuario son las 11:59

casi casi pero no
espera 1 minuto más genio
```

```
# Si hay 3+ personas en los primeros 2 segundos
⚡ BATALLA CAMPAL

@Usuario1, @Usuario2 y @Usuario3 en 2 segundos
esto es el salvaje oeste hermano

ganador: @Usuario1 por 0.001s
los demás lloran 😭
```

```
# Si alguien gana justo después de ser mencionado
👀 @Usuario1: "no voy a ganar hoy"
[2 segundos después]
@Usuario1: pole

TÍO
acabas de mentir a toda la comunidad
pero ganaste así que todo bien 🤝
```

```
# Si alguien lleva 100 días sin ganar
💀 @Usuario hace 100 días que no ganas

hermano
100 DÍAS

¿estás bien? ¿necesitas ayuda?
mañana lo intentas a las 11:59:58 y ya está
```

```
# Si alguien pierde por 0.001 segundos
😬 @Usuario perdiste por 0.001 segundos

literalmente parpadeaste
eso es todo
un parpadeo entre tú y la gloria

F en el chat 💀
```

```
# Modo equipos: Team ganador
🔥 TEAM ROJO GANA

7 días de batalla
resultado final: 2847 - 2341

@Usuario1 MVP con 847 pts
el resto: también estuvieron ahí supongo

recompensas enviadas 🏆
```

```
# Si detecta que alguien usa macro (sospecha)
🤨 @Usuario

10 poles perfectas seguidas a las 12:00:00
siempre 12:00:00.000

o eres un dios
o tienes un script

admin revisa esto porfa
```

```
# Si alguien vuelve después de suspensión
🔄 @Usuario ha vuelto de su time-out

24 horas de reflexión
esperemos que hayas aprendido

segunda oportunidad tío
no la cagues 🤝
```

```
# Cuando el bot se reinicia/vuelve online
👋 buenas chat he vuelto

preparaos que en [X minutos] abrimos pole
el que pestañea pierde 👁️
```

```
# Logro desbloqueado: EL NANO?????????
🏎️ @Usuario acaba de desbloquear: EL NANO?????????

3:33 DE LA MAÑANA TÍO
literalmente la hora del Fernando Alonso

esto es arte hermano
[Embed: GIF del nano con el casco]
```

```
# Logro desbloqueado: Muerto por Dentro
⚰️ @Usuario ha desbloqueado: Muerto por Dentro

20 veces segundo
20 VECES

hermano en algún momento tienes que plantearte cosas
pero hey al menos eres constante 💀
```

```
# Logro desbloqueado: Payaso Oficial
🤡 @Usuario nuevo logro: Payaso Oficial

10 strikes por intentarlo antes de las 12h
y sigues aquí dándole

no sé si eres valiente o directamente no aprendes
pero respeto la dedicación tío 🎪
```

```
# Logro desbloqueado: Villano del Server
👹 @Usuario es oficialmente: Villano del Server

5 rachas de +30 días rotas
hermano eres el malo de la película

la gente te odia pero yo te respeto
alguien tiene que ser el villano 😈
```

```
# Si alguien hace pole a las 6:66
🤨 @Usuario son las 6:66

espera
eso ni existe tío

cómo has...? sabes qué da igual
+10 puntos por confundirme
```

---

## 🏅 Sistema de Logros (Achievements)

### Logros Básicos
- 🏁 **Primera Sangre** - Tu primer pole
- 🌟 **10 Poles** - Alcanza 10 poles totales
- 💫 **50 Poles** - Alcanza 50 poles totales
- ⭐ **100 Poles** - Alcanza 100 poles totales
- 👑 **500 Poles** - Leyenda absoluta

### Logros de Poles Críticas
- 💎 **Cazador de Críticas** - 10 poles críticas
- 💎💎 **Maestro de Críticas** - 50 poles críticas
- 💎💎💎 **Dios de las Críticas** - 100 poles críticas
- ⏰ **Perfección Absoluta** - Pole a las 12:00:00 exactas
- ⚡ **Rayo** - 10 poles en primeros 3 segundos

### Logros de Rachas
- 🔥 **En Racha** - 3 días consecutivos
- 🔥🔥 **Semana Perfecta** - 7 días consecutivos
- 🔥🔥🔥 **Mes Imparable** - 30 días consecutivos
- 👑 **Centurión** - 100 días consecutivos
- 💎 **Inmortal** - 365 días consecutivos

### Logros Especiales (Difíciles)
- 🌅 **Friki total** - 10 poles en los primeros 2 segundos
- 🎯 **Precisión Láser** - 20 poles críticas seguidas
- 🛡️ **Defensor Invicto** - 30 días seguidos en tu servidor
- 💀 **Asesino de Récords** - Rompe 50 récords personales
- 🌟 **Leyenda** - Top 3 global por 30 días

### Logros Ocultos (No se muestran hasta conseguirlos)
- 🦉 **Búho Nocturno** - Estar activo en Discord toda la noche hasta las 12h
- 🎲 **Afortunado??** - Ser el ultimo en conseguir el pole por 3 días seguidos (sólo pole normal aplicable)
- 👻 **Fantasma** - Ganar después de 30 días sin participar
- 🔍 **Dataminer** - Descubrir y escribir el texto secreto oculto en el código (definido por admin)
- 🎯 **Explorador** - Encontrar 3 easter eggs ocultos del bot
- 🏎️ **EL NANO?????????** - Hacer pole exactamente a las 3:33 (hora del Fernando Alonso hermano)
- 🌚 **Insomnio Crónico** - Hacer pole 7 días seguidos entre las 3:00 y 5:00 AM
- 🎰 **Apostador** - Hacer pole exactamente a las 7:77... espera eso no existe, hazlo a las 7:07
- 🤡 **Payaso Oficial** - Perder 10 poles por intentarlo antes de las 12h (y seguir intentándolo)
- ⚰️ **Muerto por Dentro** - Llegar segundo 20 veces (tan cerca y tan lejos tío)
- 🐌 **Récord Mundial** - Ser el último en hacer pole del día 15 veces (premio al más lento)
- 🎭 **Actor del Año** - Decir "no voy a intentarlo hoy" y ganarlo en los primeros 3 segundos
- 🍕 **Gamer Auténtico** - Hacer pole exactamente a las 4:20 (ya sabes)
- 👹 **Villano del Server** - Romper rachas de más de 30 días de otros 5 veces
- 🎪 **Circo Completo** - Acumular 10 strikes en total (histórico)

### Logros de Puntos Totales (Nuevos Milestones)
Se desbloquean al alcanzar puntos acumulados (post-escala que se defina). Nombres tentativos:

| Puntos | Nombre | Descripción | Rareza (placeholder) |
|--------|--------|-------------|----------------------|
| 10 | El Comienzo | Primeros pasos en el camino del pole | 95% |
| 100 | Persistente | Ya no fue suerte: sigues aquí | 80% |
| 1,000 | Umbral Experto | Empiezas a ser reconocido | 50% |
| 10,000 | Camino del Maestro | Demuestras constancia real | 25% |
| 100,000 | Maestro del Pole | Dominio avanzado | 10% |
| 1,000,000 | Ascenso Divino | ¿Leyenda? Te acercas a la mitología | 1% |
| 10,000,000 | Nuevo Dios | Estás en otra liga | 0.1% |
| 100,000,000 | Entidad Superior | Más concepto que jugador | 0.01% |

Nota: Los porcentajes son estimaciones temporales; en producción se calcularán dinámicamente:
`porcentaje = jugadores_con_logro / jugadores_activos * 100`.

Visualización sugerida:
```
🏆 LOGRO DESBLOQUEADO: "Maestro del Pole"
Puntos totales: 100,000
Solo el 9.4% de los jugadores han llegado aquí.
```

Para rarezas extremas (<0.05%) se puede añadir borde especial o animación.

---

## 🌐 Sistema de Representación de Servidor

### ¿Cómo Funciona?

Cada usuario puede elegir QUÉ servidor representa en el ranking global.

### Comando
```
/represent
```

**Respuesta del bot:**
```
🌍 REPRESENTACIÓN GLOBAL 🌍

Estás en varios servidores con Pole Bot:
1. 🏠 Los Insomnes (250 pts aquí)
2. 🎮 Gaming Zone (180 pts aquí)
3. 💼 Work & Chill (90 pts aquí)

¿Cuál quieres representar en el ranking global?

[Botón: Los Insomnes] [Botón: Gaming Zone] [Botón: Work & Chill]

Nota: Puedes cambiar esto cuando quieras
```

### Visualización en Leaderboard Global

```
🌍 TOP 10 GLOBAL 🌍

1. 💎 @PoleKing      15,240 pts | Representa: 🏆 Elite Gamers
2. 💎 @FastHands     14,890 pts | Representa: ⚔️ Warriors
3. 👑 @DarkPhoenix    8,450 pts | Representa: 🏠 Los Insomnes ← ¡Eres tú!
```

### Sistema de Lealtad

**Bonus por Lealtad:**
- Si representas el mismo servidor por 30 días: +50 pts
- Si representas el mismo servidor por 90 días: +150 pts
- Si representas el mismo servidor por 365 días: +500 pts + Badge "Leal"

**¿Por qué?** Para premiar a quienes tienen compromiso con su comunidad.

---

## 🎨 Ideas Extra Creativas

### 1. Temas/Skins Estacionales
```
# Halloween (Octubre)
🎃 ¡POLE TERRORÍFICO! 🎃
@Usuario captura el alma del día
+25 puntos espectrales 👻

# Navidad (Diciembre)
🎄 ¡POLE NAVIDEÑO! 🎄
@Usuario encuentra el regalo bajo el árbol
+25 puntos festivos 🎅

# Año Nuevo (1 de Enero)
🎆 ¡PRIMER POLE DEL AÑO! 🎆
@Usuario empieza 2026 con el pie derecho
+50 puntos de celebración 🥳
```

### 2. Eventos Especiales (Admin)
```
/event create doublepoints 24h
/event create hardmode 1h        # Solo primeros 10 segundos
/event create teammode           # Dividir servidor en equipos
```

### 3. Predicciones del Bot
```
🔮 PREDICCIÓN DEL DÍA 🔮

Basado en historial y patrones:
- @DarkPhoenix: 85% probabilidad de ganar
- @SpeedRunner: 10% probabilidad
- @NightOwl: 5% probabilidad

¿Sorprenderán hoy? 🤔
```

### 4. Rivalidades Detectadas
```
⚔️ RIVALIDAD EN CURSO ⚔️

@DarkPhoenix vs @SpeedRunner

Historial cara a cara:
- DarkPhoenix: 45 victorias
- SpeedRunner: 43 victorias
- Diferencia: +2

¡La batalla continúa! 🔥
```

### 5. Modo Equipos (Evento Temporal)
```
👥 MODO EQUIPOS ACTIVADO 👥

Se han creado 2 equipos aleatorios:
🔴 Team Rojo (12 miembros)
🔵 Team Azul (11 miembros)

Cada pole suma puntos al equipo.
El equipo ganador después de 7 días recibe:
+100 puntos por miembro 🏆

¡A competir!
```

---

## 🔒 Prevención de Trampas

### Anti-Bot
- Verificar que sean cuentas reales (edad mínima 7 días)
- Flag si tiempo de respuesta es < 100ms constantemente
- Requiere verificación manual del admin

### Anti-Spam
- Cooldown de 1 segundo entre intentos
- Después de 3 intentos en 10 segundos: warning
- Spam extremo: strike automático

### Anti-Macro
- Detectar patrones sospechosos (siempre exactamente a las 12:00:00)
- Si 10+ poles perfectas seguidas: revisión manual
- Admin puede marcar pole como "sospechosa"

### Sistema de Reportes
```
/report @usuario <razón>
```
- Los usuarios pueden reportar comportamiento sospechoso
- Admins revisan en panel de moderación
- Historial de reportes guardado

---

## 💭 Filosofía de Diseño

### Principios Core
1. ✅ **Diversión primero** - Es un juego, no un trabajo
2. ✅ **Competitivo pero amigable** - Ganar es cool, pero perder no es el fin
3. ✅ **Balance constante** - Nadie debe ser imbatible
4. ✅ **Personalidad única** - El bot tiene carácter, no es un robot frío
5. ✅ **Comunidad sobre individual** - Fomenta interacción entre usuarios

### ¿Qué hace este bot ÚNICO?
- 😎 **Personalidad** - El bot habla como una persona, con humor
- 🎯 **Balance perfecto** - Perder una racha no es devastador
- 🏆 **Progresión clara** - Siempre hay algo que alcanzar
- 🌍 **Global pero local** - Compites globalmente, representas localmente
- 🎨 **Vivo y dinámico** - Eventos, temas, cambios constantes

---

## 🚀 Plan de Implementación

### MVP (Fase 1) - Lo Esencial
1. ✅ Detección exacta de "pole"
2. ✅ Sistema de Pole Crítica vs Normal vs Tardía
3. ✅ Sistema de puntos balanceado
4. ✅ Sistema de rachas (máx 365 días)
5. ✅ Warnings discretos (3 strikes)
6. ✅ Notificaciones básicas (reset + victoria)
7. ✅ Comandos básicos (/stats, /leaderboard local)

### Fase 2 - Personalidad y Social
8. ✅ Sistema de rangos con emojis
9. ✅ Logros/Achievements
10. ✅ Mensajes con humor y variedad
11. ✅ Sistema de timezones
12. ✅ /leaderboard interactivo con botones
13. ✅ Sistema de representación de servidor

### Fase 3 - Global y Avanzado
14. ✅ Ranking global multi-servidor
15. ✅ Panel /config interactivo
16. ✅ Rivalidades automáticas
17. ✅ Predicciones del bot
18. ✅ Eventos especiales
19. ✅ Temas estacionales

### Fase 4 - Polish y Extras
20. ✅ Modo equipos
21. ✅ Sistema anti-trampas robusto
22. ✅ Dashboard web (opcional)
23. ✅ Easter eggs ocultos
24. ✅ Logros secretos

---

## 📝 Notas Finales del Diseño v1.0

### ⚠️ ESTADO: DESARROLLO ACTIVO

Este documento define la **versión 1.0** del sistema, actualmente en fase de desarrollo.
No se ha publicado ninguna versión pública todavía.

### Decisiones Confirmadas (v1.0)

✅ **Pole Crítica:** 20 pts directos (sin multiplicador separado)  
✅ **Pole Secundón:** 11 pts fijos  
✅ **Pole Normal:** 10 pts base  
✅ **Pole Marranero:** 7 pts base  
✅ **NO hay Madrugador** - Descartado  
✅ **Sistema de rachas:** Hitos progresivos hasta 2.5x en 300 días, máximo 365 días  
✅ **NO hay redondeos** - Decimales permitidos (13.2 pts es válido)  
✅ **Penalties:** Advertencias discretas (🚫 reactions), strikes system  
✅ **Logros ocultos:** Incluye "Dataminer" con texto secreto personalizable  
✅ **NO logros sociales** - No se detectan felicitaciones ni comportamiento social  
✅ **Leaderboard:** Slash command con botones global/local  
✅ **Representación:** Usuarios eligen servidor para ranking global  

---

## 🎯 ¿Siguiente Paso?

**Opción A:** Empezar a implementar el MVP (Fase 1)  
**Opción B:** Refinar más el diseño antes de codear  
**Opción C:** Crear mockups visuales de los embeds  
**Opción D:** Tu idea/cambio/locura 🚀

---

*Este diseño tiene ESENCIA. Ahora toca darle vida.* ✨

Son las 12:00 y el pole está servido en bandeja.
¿Alguien tiene hambre? 😎

@RolePole
```

```
🔥 ¡A CORRER! 🔥

12:00 en punto. El que pestañea, pierde.
Suerte, la vais a necesitar 😏

@RolePole
```

### Notificación de Victoria

**Pole Crítica:**
```
💎 ¡POLE CRÍTICA! 💎

@Usuario se lleva el primer mensaje del día
⏱️ Tiempo: 12:00:03

💰 +25 puntos | 🔥 Racha: 12 días (+12)
🎯 Total ganado: 37 puntos

¡Imparable! 🔥
```

**Pole Normal:**
```
🏁 ¡POLE! 🏁

@Usuario llega primero (pero no fue el primer mensaje)
⏱️ Tiempo: 12:05:30

💰 +10 puntos | 🔥 Racha: 5 días (+5)
🎯 Total ganado: 15 puntos

¡Buen trabajo! 👏
```

**Pole Perfecta (12:00:00):**
```
🌟 ¡POLE PERFECTA! 🌟

@Usuario acaba de hacer historia
⏱️ Tiempo: 12:00:00 (PERFECTO)

💎 +25 (crítica) +10 (perfección) +8 (racha)
🎯 Total ganado: 43 puntos

¡ESTO ES LEYENDA! 🏆
```

### Configuración de Notificaciones
```
/notify reset on/off          # Avisar cuando se abre pole
/notify winner on/off         # Avisar cuando alguien gana
/notify mention @role         # Mencionar rol específico
```

---

## 📱 Comandos (Slash Commands Modernos)

### Comandos de Usuario

```
/pole                         # Info sobre el pole actual
/stats [@usuario]             # Tus stats o las de otro
/leaderboard [global/local]   # Ver ranking (con botones interactivos)
/streak                       # Ver tu racha
/achievements                 # Ver tus logros
/profile [@usuario]           # Ver perfil completo
/represent <servidor>         # Elegir servidor para ranking global
/mytimezone <zona>            # Tu zona horaria personal
```

### Comandos de Admin

```
/setpolechannel              # Configurar canal de pole
/settimezone <zona>          # Zona del servidor
/notify <opciones>           # Configurar notificaciones
/warn @usuario <razón>       # Dar strike manual
/forgive @usuario            # Perdonar strikes
/timeout @usuario <horas>    # Suspensión temporal
/config                      # Abrir panel de configuración
/enableglobal <yes/no>       # Participar en ranking global
```

### Comandos de Información

```
/help                        # Ayuda general
/rules                       # Reglas del pole
/info                        # Info del sistema
```

---

## 🎮 /leaderboard - Sistema Interactivo

### Vista Local (Servidor)

```
🏆 LEADERBOARD - Los Insomnes 🏆

1. 💪 @DarkPhoenix        1,450 pts | 🔥 23 días
2. ⚔️ @SpeedRunner        890 pts  | 🔥 8 días
3. 🛡️ @NightOwl           720 pts  | 🔥 15 días
4. 🏃 @QuickFingers       580 pts  | 🔥 3 días
5. ⚔️ @PoleHunter         510 pts  | 🔥 1 día

[Botón: 🌍 Ver Global] [Botón: 📊 Filtros]
```

### Vista Global

```
🌍 LEADERBOARD GLOBAL 🌍

1. 💎 @LegendaryUser     15,340 pts | 🌟 Servidor: Elite Gaming
2. 💎 @PoleGod          14,120 pts | 🌟 Servidor: Night Crew
3. 👑 @FastFingers      12,890 pts | 🌟 Servidor: Speed Demons
4. 💪 @DarkPhoenix       8,450 pts | 🌟 Servidor: Los Insomnes
5. 💪 @ChampionPole      7,920 pts | 🌟 Servidor: Pro Polers

[Botón: 🏠 Ver Local] [Botón: 🎯 Ver tu Posición]

Representas a: Los Insomnes
Tu posición global: #47 de 2,341
```

---

## ⚙️ /config - Panel de Configuración Interactivo

```
⚙️ CONFIGURACIÓN DEL SERVIDOR ⚙️

📍 Canal de Pole: #pole-diario
🌍 Zona Horaria: Europe/Madrid (UTC+1)
⏰ Hora de Reset: 12:00

🔔 Notificaciones:
  └─ Reset: ✅ Activado (@Polers)
  └─ Victoria: ✅ Activado
  └─ Rachas perdidas: ❌ Desactivado

🌐 Ranking Global: ✅ Participando
📊 Privacidad: Público

[Botón: ✏️ Editar Canal]
[Botón: 🌍 Cambiar Timezone]
[Botón: 🔔 Notificaciones]
[Botón: 🌐 Configurar Global]
```

---

## 💬 Personalidad del Bot (ESENCIA)

### Tono General
- 😎 **Cool pero no arrogante**
- 😄 **Divertido pero no spam**
- 💪 **Motivador pero no cursi**
- 🎯 **Directo y claro**

### Ejemplos de Respuestas con Humor

**Cuando alguien llega tarde:**
```
😴 @Usuario, llegaste 3 horas tarde...
   El pole se ganó hace rato, campeón.
   Pon el despertador para mañana 😉
```

```
🐌 Lento pero seguro, ¿eh @Usuario?
   Lástima que @Winner ya ganó.
   ¡A entrenar esos dedos para mañana! 💪
```

**Cuando alguien hace pole perfecta:**
```
🤯 @Usuario... ¿acabas de...?
   SÍ. POLE A LAS 12:00:00 EXACTAS.
   
   Esto es... esto es ARTE PURO 🎨
   +35 puntos. TE LOS MERECES.
```

**Cuando alguien rompe su récord:**
```
🎉 ¡RÉCORD PERSONAL!

@Usuario acaba de superar su mejor marca.
Antes: 45 días de racha
Ahora: 46 días de racha

Keep going, campeón 💪🔥
```

**Cuando alguien pierde una racha larga:**
```
💔 Moment

## 🏅 Sistema de Logros (Achievements)

### Logros de Poles
- 🏁 **Primera Pole**: Gana tu primera pole
- 🌟 **10 Poles**: Alcanza 10 poles totales
- 💫 **50 Poles**: Alcanza 50 poles totales
- ⭐ **100 Poles**: Alcanza 100 poles totales
- 👑 **500 Poles**: Leyenda del servidor

### Logros de Poles Críticas
- 💎 **Cazador de Críticas**: 10 poles críticas
- 💎💎 **Maestro de Críticas**: 50 poles críticas
- ⏰ **Perfección Absoluta**: Pole exactamente a las 12:00:00

### Logros de Rachas
- 🔥 **En Racha**: 3 días consecutivos
- 🔥🔥 **Semana Perfecta**: 7 días consecutivos
- 🔥🔥🔥 **Mes Imparable**: 30 días consecutivos
- 👑 **Leyenda**: 100 días consecutivos
- 🌟 **Año Perfecto**: 365 días consecutivos (casi imposible)

### Logros Especiales
- 🌅 **Madrugador**: Pole en el primer segundo (12:00:00-12:00:01)
- 🌙 **Noctámbulo**: No dormir esperando las 12h (detección por actividad)
- 🎯 **Precisión Suiza**: 10 poles en los primeros 5 segundos
- 🛡️ **Defensor**: Ganar 7 días seguidos en TU servidor

## 🌐 Sistema Global Multi-Servidor

### Ranking Global (Opcional)
```
!enableglobal yes/no
```

### Tabla Global
```
🌍 TOP POLERS GLOBALES

1. 👑 Usuario1 (Servidor: Amigos)    - 2,450 pts | 45 servidores
2. 🥈 Usuario2 (Servidor: Gaming)    - 2,100 pts | 32 servidores
3. 🥉 Usuario3 (Servidor: Tech)      - 1,890 pts | 28 servidores
```

### Privacidad
- Los usuarios pueden optar por salir del ranking global
- Solo se comparten estadísticas, no mensajes ni datos sensibles

## 📱 Comandos Completos

### Comandos de Usuario
```
!pole                    # Hacer pole (solo vale si escribes "pole")
!stats                   # Tus estadísticas personales
!stats @usuario          # Ver stats de otro usuario
!leaderboard / !top      # Ranking del servidor
!globalrank              # Ranking global (si está activo)
!achievements / !badges  # Ver tus logros
!streak                  # Ver tu racha actual
!mytimezone <zona>       # Configurar tu zona horaria personal
```

### Comandos de Admin
```
!setpolechannel              # Configurar canal de pole
!settimezone <zona>          # Configurar zona del servidor
!notify <tipo> <on/off>      # Configurar notificaciones
!notify mention @role        # Mencionar rol en notificaciones
!penalty @usuario <razón>    # Dar penalty manual
!removepenalty @usuario      # Quitar última penalty
!resetstreak @usuario        # Resetear racha de un usuario
!giveachievement @usuario <logro>  # Dar logro especial
!enableglobal <yes/no>       # Participar en ranking global
!config                      # Ver configuración actual
```

### Comandos de Información
```
!polehelp              # Ayuda general
!polerules             # Reglas del pole
!poleinfo              # Info sobre el sistema
```

## 🎨 Ideas Extra Creativas

### 1. Temas/Skins
- Cambiar emojis y colores según temporada
- Tema Halloween, Navidad, etc.

### 2. Eventos Especiales
```
!poleevent doublepoints     # Fin de semana: puntos dobles
!poleevent hardmode         # Modo difícil: solo primeros 3 segundos
```

### 3. Predicciones
```
Bot: "🔮 Predicción: @Usuario1 tiene 85% de ganar hoy (basado en historial)"
```

### 4. Rivalidades
```
Bot: "⚔️ Rivalidad detectada entre @User1 y @User2"
     "@User1: 45 poles | @User2: 43 poles"
     "¡La batalla continúa!"
```

### 5. Modo Competitivo por Equipos
- Dividir el servidor en equipos
- Competir por puntos totales
- Temporadas mensuales

## 🔒 Prevención de Trampas

### Anti-Bot
- Verificar que sean cuentas reales
- Captcha opcional para nuevos usuarios

### Anti-Spam
- Cooldown entre intentos
- Ban temporal por spam

### Anti-Macro
- Detectar patrones sospechosos
- Requerir verificación manual si es muy rápido

---

## 💭 Reflexiones de Diseño

### ¿Qué priorizamos?
1. ✅ **Simplicidad**: Fácil de entender
2. ✅ **Justo**: Reglas claras, sin ambigüedades
3. ✅ **Engagement**: Que la gente quiera volver cada día
4. ✅ **Diversión**: Competitivo pero amigable

### ¿Qué implementamos primero?
**MVP (Mínimo Viable Product):**
1. Detección de "pole" exacta
2. Sistema de rachas básico
3. Penalties automáticas
4. Notificaciones de reset y victoria
5. Estadísticas con puntos

**Fase 2:**
6. Zonas horarias
7. Logros/Achievements
8. Comandos avanzados

**Fase 3:**
9. Ranking global
10. Eventos especiales
11. Temas y personalización

---

## 🤔 Preguntas para Ti

1. **Penalties**: ¿Te gusta el sistema automático? ¿Muy estricto o muy suave?
2. **Rachas**: ¿Incluimos "Freeze Cards" o es muy complejo?
3. **Global**: ¿Lo hacemos desde el principio o en fase 2?
4. **Notificaciones**: ¿Mencionar roles o solo mensaje general?
5. **Puntos vs Solo Contador**: ¿Prefieres sistema de puntos o solo contar poles?
6. **Nombre del comando**: ¿`!pole` o solo escribir "pole" sin comando?

**¿Qué te parece? ¿Cambiamos algo? ¿Añadimos más locuras? 🚀**
