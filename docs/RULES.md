# 📋 Reglas del Pole Bot

## ¿Qué es una Pole Válida?

Un mensaje que contenga **SOLO** la palabra "pole" (case insensitive, sin espacios extra).

**Ejemplos válidos:** 
- `pole`, `Pole`, `POLE`, `PoLe`, `pOlE`

**Ejemplos NO válidos:** 
- `pole!`, `pole mañanera`, `hola pole`, `p o l e`, `pole `, ` pole`

---

## 🏁 Tipos de Pole y Ventanas Horarias

### ⚡ Regla Fundamental: **TODOS PUEDEN GANAR CADA DÍA**

**Cada usuario** puede hacer su pole diario y mantener su racha. No hay límite de ganadores.

**Pero el orden importa:**
- **Primero** que escribe "pole" → Pole **Crítica** 💎 (20 pts directos)
- **Segundo** que escribe "pole" → Pole **Secundón** 🥈 (11 pts fijos)
- **Resto** → Pole Normal/Marranero según la hora

---

### Categorías por Horario

#### 1) Pole Crítica 💎 (SOLO el primero del día)
- Usuario: El primer "pole" del día
- Puntos base: **20 pts** (directo, sin multiplicadores)
- Cuenta para racha: ✅ Sí

#### 2) Pole Secundón 🥈 (SOLO el segundo del día)
- Usuario: El segundo "pole" del día
- Puntos base: **11 pts** (fijo, sin importar la hora)
- Cuenta para racha: ✅ Sí

#### 3) Pole Normal 🏁 (Tercero en adelante, antes de las 12:00)
- Ventana: **08:00–12:00**
- Puntos base: **10 pts**
- Cuenta para racha: ✅ Sí

#### 4) Pole Marranero 🐷 (Después de las 12:00)
- Ventana: **≥ 12:00** (mediodía en adelante)
- Puntos base: **7 pts**
- Cuenta para racha: ✅ Sí
- Se trackea con contador propio en estadísticas

---

### Resumen de Puntos Base

| Posición | Nombre | Puntos Base |
|----------|--------|-------------|
| 1º | Crítica 💎 | **20 pts** |
| 2º | Secundón 🥈 | **11 pts** |
| 3º+ (08:00–12:00) | Normal 🏁 | **10 pts** |
| 3º+ (≥12:00) | Marranero 🐷 | **7 pts** |

**Nota:** El Secundón siempre vale 11 pts (sin importar si es antes o después de las 12h).

---

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
😬 @Usuario, cuidado... Strike 2/3
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
🛑 @Usuario - Strike 3/3

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
