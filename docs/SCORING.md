# 📊 Sistema de Puntos y Rachas

## Fórmula de Puntuación

Puntos del día = `PuntosBase(posición)` × `MultiplicadorRacha`

- `PuntosBase(posición)` = 20 (Crítica 1º) | 11 (Secundón 2º) | 10 (Normal 3º+) | 7 (Marranero ≥12:00)
- `MultiplicadorRacha` = progresivo (ver abajo), con tope global **2.5x**

**Notas:**
- Los puntos base ya están definidos según tu posición (no hay multiplicador crítico separado).
- La racha multiplica el total.
- Opcional: bonus de precisión (12:00:00 ± 1s) se puede añadir más adelante.

### Precisión y Decimales
- El multiplicador de racha se aplica SOLO al premio del día (no al total acumulado).
- Con bases `20/11/10/7` y escalones de `+0.1x`, los casos de `11` y `7` pueden producir decimales (ej. `11 × 1.2 = 13.2`).
- No se realizan redondeos: se guarda y muestra el valor exacto resultante.

---

## Ejemplos Prácticos

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

### Milestones Cosméticos

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

## 🛡️ Protección Anti-Lose/Lose

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

---

## 💸 Cómo se Pierden Puntos

| Acción | Penalización |
|--------|--------------|
| Strike 1 | -0 pts (solo advertencia) |
| Strike 2 | -5 pts |
| Strike 3 | -10 pts + suspensión |
| Spam severo | -25 pts |

**Protección:** Nunca puedes bajar de 0 puntos (no hay puntos negativos).

---

## 🎖️ Sistema de Rangos

Tu **rango** aparece automáticamente junto a tu nombre en estadísticas y leaderboards.

**Basado en:** Puntos totales + Poles críticas + Mejor racha

### Tabla de Rangos

| Rango | Requisitos | Emoji | Descripción |
|-------|-----------|-------|-------------|
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
