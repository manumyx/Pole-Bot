# 💬 Comandos del Pole Bot v1.0

Lista completa de comandos disponibles organizados por categoría.

---

## 👤 Comandos de Usuario

### `/profile [usuario]`
Muestra las estadísticas de un usuario.

**Parámetros:**
- `usuario` (opcional): Usuario a consultar (por defecto: tú mismo)

**Información mostrada:**
- Puntos de temporada actual
- Puntos lifetime (carrera completa)
- Racha actual y mejor racha
- Total de poles
- Poles por categoría (Crítica, Veloz, Normal, Marranero)
- Rango actual con badge
- Servidor representado

**Ejemplo de uso:**
```
/profile
/profile usuario:@Shuu
```

**Salida:**
```
📊 Perfil de Shuu

🏆 Temporada Actual
💰 Puntos: 450.5 pts
🥈 Rango: Plata Distinguida

📈 Carrera Completa
💎 Puntos totales: 1205.8 pts
🏁 Total poles: 42

🔥 Rachas
⚡ Actual: 12 días (x1.2)
🏆 Mejor: 25 días

📊 Estadísticas
🏆 Críticas: 5
⚡ Veloces: 15
🎯 Poles: 18
🐷 Marraneros: 4

🌐 Representación
Servidor: Mi Comunidad
```

---

### `/leaderboard [vista] [alcance] [temporada]`
Muestra el ranking del servidor o global.

**Parámetros:**
- `vista`: `personas` (default) o `servers`
- `alcance`: `local` (default) o `global`
- `temporada`: Ver dropdown de temporadas disponibles

**Opciones de Temporada:**
- 🌟 **Lifetime** - Carrera completa (todas las temporadas)
- 🔥 **Temporada Actual** - Temporada en curso
- 📜 **Pre Season** - Temporada de prueba (si existe)
- 📅 **Season 2024** - Temporadas finalizadas

**Ejemplos:**
```
/leaderboard
/leaderboard vista:personas alcance:global
/leaderboard vista:servers alcance:local
/leaderboard temporada:Season 2024
```

**Salida (Personas - Local):**
```
🏆 TOP 10 - Mi Servidor
Temporada: Season 2025

1. 💎 @Usuario1 — 2450.5 pts
2. 🔮 @Usuario2 — 1680.2 pts
3. 💎 @Usuario3 — 1120.0 pts
4. 🥇 @Usuario4 — 890.5 pts
...
```

**Salida (Servidores - Global):**
```
🌐 RANKING GLOBAL DE SERVIDORES
Temporada: Lifetime

1. 🥇 Comunidad Alpha — 15,420 pts (25 miembros)
2. 🥈 Servidor Beta — 12,890 pts (18 miembros)
3. 🥉 Guild Gamma — 10,350 pts (22 miembros)
...
```

---

### `/polehelp`
Tutorial interactivo sobre cómo usar el bot.

**Muestra:**
- Cómo funciona el juego
- Sistema de puntos
- Rachas y multiplicadores
- Comandos disponibles
- Enlaces a documentación completa

**Ejemplo:**
```
/polehelp
```

---

## ⚙️ Comandos de Administración

### `/settings`
Configuración interactiva del bot (solo administradores).

**Menú de Opciones:**

#### 1️⃣ Canal de Pole
Establece el canal donde:
- Se envían notificaciones de apertura
- Se acepta la palabra "pole"

**Cómo configurar:**
1. Usa `/settings`
2. Selecciona "📺 Canal de Pole" del menú
3. Menciona el canal (ej: #pole-diario)

#### 2️⃣ Rango Horario
Define el rango de horas donde puede abrirse el pole.

**Formato:** HH:MM - HH:MM (24h)

**Ejemplos:**
- `12:00 - 20:00` → Entre mediodía y 8 PM
- `08:00 - 23:00` → Entre 8 AM y 11 PM
- `18:00 - 22:00` → Solo tarde-noche

**Cómo configurar:**
1. Usa `/settings`
2. Selecciona "🕐 Rango Horario"
3. Ingresa formato: `HH:MM - HH:MM`

#### 3️⃣ Notificaciones
Activa/desactiva notificaciones automáticas.

**Opciones:**
- **Apertura**: Notifica cuando se abre el pole
- **Resumen**: Resumen diario a medianoche

**Recomendación:** Mantener ambas activadas

#### 4️⃣ Ping de Rol
Configura qué ping usar en notificaciones.

**Modos:**
- **Sin ping**: Solo embed, sin menciones
- **Rol específico**: Menciona un rol (ej: @Pole Hunters)
- **@everyone**: Menciona a todos

**Cómo configurar:**
1. Usa `/settings`
2. Selecciona "👥 Ping de Rol"
3. Elige el modo
4. Si elegiste "Rol específico", menciona el rol

#### 📋 Ver Configuración
Muestra la configuración actual del servidor.

**Información:**
- Canal configurado
- Rango horario
- Estado de notificaciones
- Modo de ping

---

## 🛠️ Comandos de Debug (Desarrollo)

> **⚠️ Nota:** Estos comandos solo funcionan si `DEBUG=1` en `.env` y eres administrador.

### `/debug badges`
Muestra todos los rangos, badges y umbrales de puntos.

```
/debug badges
```

**Salida:**
```
🎖️ Rangos y Umbrales (DEBUG)

💎 Rubí — Rubí Maestro • ≥ 2000 pts
🔮 Amatista — Amatista Élite • ≥ 1500 pts
💎 Diamante — Diamante Supremo • ≥ 1000 pts
🥇 Oro — Oro Imperial • ≥ 600 pts
🥈 Plata — Plata Distinguida • ≥ 300 pts
🥉 Bronce — Bronce Valiente • ≥ 100 pts
```

---

### `/debug addpoints <usuario> <puntos> [alcance]`
Añade puntos a un usuario manualmente (testing).

**Parámetros:**
- `usuario`: Usuario al que añadir puntos
- `puntos`: Cantidad de puntos (puede ser decimal)
- `alcance`: `lifetime`, `season`, o `both` (default: both)

**Ejemplos:**
```
/debug addpoints usuario:@Shuu puntos:50.5
/debug addpoints usuario:@Shuu puntos:100 alcance:season
```

**Salida:**
```
✅ Puntos añadidos a @Shuu

🏆 Lifetime: +50.5 → 350.5 pts (calculado)
📅 Season (season_2025): +50.5 → 150.5 pts
```

---

### `/debug fakepole <usuario> [retraso] [categoria] [fecha]`
Simula un pole en el pasado (testing de rachas).

**Parámetros:**
- `usuario`: Usuario para simular pole
- `retraso`: Minutos de retraso (0-500, default: 5)
- `categoria`: `critical`, `fast`, `normal`, `marranero`
- `fecha`: Fecha del pole (YYYY-MM-DD, default: hoy)

**Ejemplos:**
```
/debug fakepole usuario:@Shuu
/debug fakepole usuario:@Shuu retraso:120 categoria:normal
/debug fakepole usuario:@Shuu fecha:2024-12-01
```

**Útil para:**
- Probar multiplicadores de racha
- Simular historial de poles
- Testing de migración de temporadas

---

### `/debug open_now`
Abre el pole AHORA mismo (sin esperar hora configurada).

```
/debug open_now
```

**Acciones:**
1. Establece hora actual como apertura
2. Envía notificación al canal configurado
3. Permite hacer pole inmediatamente

**Salida:**
```
✅ ¡Pole abierto AHORA! (13:45:32)
💬 Escribe pole en #pole-diario para probarlo.
```

---

### `/debug reset_date [usuario]`
Resetea `last_pole_date` y elimina poles de hoy (testing).

**Parámetros:**
- `usuario` (opcional): Usuario a resetear (default: tú mismo)

**Acciones:**
1. Resetea `last_pole_date` a `None`
2. Elimina todos los poles de hoy del usuario
3. Permite hacer pole nuevamente

**Uso típico:**
```
1. /debug reset_date
2. /debug open_now
3. Escribe "pole"
4. Repite para probar múltiples veces
```

**Salida:**
```
✅ Reseteado para @Shuu
• last_pole_date → None
• Poles eliminados hoy: 1
💡 Ahora puedes hacer /debug open_now y volver a polear.
```

---

## 📝 Notas sobre Comandos

### Permisos
- **Usuario**: Cualquiera puede usar comandos de usuario
- **Administrador**: Se requiere permiso de Administrador para `/settings`
- **Debug**: Se requiere `DEBUG=1` en .env y ser administrador/owner

### Cooldowns
- No hay cooldowns en comandos de consulta
- Los comandos de debug no tienen límites (solo para testing)

### Mensajes Efímeros
Algunos comandos usan mensajes efímeros (solo tú los ves):
- `/settings` → Solo el admin ve la configuración
- `/debug` → Solo quien ejecuta ve el resultado
- `/polehelp` → Solo quien pide ayuda la ve

### Autocomplete
Algunos parámetros tienen autocomplete inteligente:
- `temporada` en `/leaderboard` → Muestra temporadas disponibles
- `usuario` en comandos → Muestra miembros del servidor

---

## 🆘 Ayuda Adicional

Si tienes problemas con algún comando:
1. Verifica que el bot tenga permisos necesarios
2. Consulta `/polehelp` para tutoriales
3. Lee la documentación completa en `/docs`
4. Contacta a un administrador del servidor

---

**Versión:** 1.0  
**Última actualización:** Diciembre 2024
