# 📱 Comandos del Bot

## Comandos de Usuario

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

## Comandos de Admin

```
/setpolechannel              # Configurar canal de pole
/settimezone <zona>          # Zona del servidor
/notify <opciones>           # Configurar notificaciones
/poleping set <@rol|everyone|none>  # Configurar ping del reset
/poleping show               # Ver ping configurado actual
/warn @usuario <razón>       # Dar strike manual
/forgive @usuario            # Perdonar strikes
/timeout @usuario <horas>    # Suspensión temporal
/config                      # Abrir panel de configuración
/enableglobal <yes/no>       # Participar en ranking global
```

## Comandos de Información

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

---

## 🌐 Sistema de Representación de Servidor

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

### Sistema de Lealtad

**Bonus por Lealtad:**
- Si representas el mismo servidor por 30 días: +50 pts
- Si representas el mismo servidor por 90 días: +150 pts
- Si representas el mismo servidor por 365 días: +500 pts + Badge "Leal"

---

## 🔔 Ping Configurable del Reset

### Modos Disponibles

- `none` → No se menciona ningún rol
- `role:<id>` → Se menciona un rol concreto configurado por admin
- `everyone` → Se permite @everyone pero requiere confirmación

### Comandos

```
/poleping set <@rol|everyone|none>
/poleping show
```

### Flujo especial @everyone

1. Admin ejecuta `set everyone`
2. Bot responde con advertencia: "⚠️ Usar @everyone puede generar spam. Confirma con /poleping confirm en 60s"
3. Admin ejecuta `/poleping confirm`
4. Se guarda configuración
5. Expira confirmación si no se ejecuta a tiempo
