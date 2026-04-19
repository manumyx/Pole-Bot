# 🏁 Reglas Oficiales de Pole Bot

## 🎯 Objetivo

Ser de los primeros en escribir `pole` cuando el bot abre el día.

## ⏱️ Flujo diario

1. Se genera una hora de apertura aleatoria por servidor.
2. El bot notifica en el canal configurado.
3. Los mensajes `pole` se clasifican por velocidad.

## 💎 Categorías y puntos base

- **Critical** (0–10 min): 20 pts
- **Fast** (10 min–3 h): 15 pts
- **Normal** (3 h–fin del día local): 10 pts
- **Marranero** (día siguiente): 5 pts

> El resultado final aplica multiplicador de racha.

## 📊 Cuotas por categoría

Calculadas sobre jugadores activos del servidor:

- Critical: 10%
- Fast: 30%

Si una categoría se llena, la participación baja a la siguiente sin bloquear la pole.

## 🌍 Regla global

Solo puedes hacer **una pole por día global** (aunque juegues en varios servidores).

## 🔥 Rachas

- Son globales (no por servidor).
- Si cumples el día, suben +1.
- Si no cumples, se pueden reiniciar.
- El marranero permite recuperar el día anterior dentro de su ventana.

## 🐷 Marranero (aclaración)

- No cuenta como segunda pole del día.
- Registra `pole_date` del día perdido.
- No permite duplicar un día ya reclamado.

## 🛟 Downtime y compensaciones

Ante incidencias reales, admins con debug pueden usar:

- `/debug compensate_downtime`
- `/debug restore_streak`
- `/debug restore_guild`

## ⚙️ Configuración mínima (`/settings`)

- Canal de pole
- Rango horario
- Notificaciones
- Ping opcional (rol o everyone)
- Idioma
