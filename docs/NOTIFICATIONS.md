# 🔔 Notificaciones y Personalidad del Bot

## Personalidad del Bot (ESENCIA)

### Tono General
El bot habla como un colega que te echa la bulla pero nunca se pasa. Directo, sin cursilerías, con humor natural y emojis que dicen algo de verdad.

**Reglas de oro:**
- Nada de "¡Felicidades campeón!" genérico → mejor "tío te has lucido 🔥"
- Nada de sermones → si la cagas, te lo dice claro pero sin drama
- Emojis con sentido → no spam, solo los que refuerzan el mensaje
- Humor sin forzar → si no sale natural, mejor directo al grano

---

## Notificaciones de Reset (A las 12:00h)

### Versión Estándar
```
🏁 POLE ABIERTO

son las 12:00 chat
a ver quién es el más rápido hoy

@RolePole (si está configurado)
```

### Versiones con Humor (Aleatorio)
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

---

## Notificaciones de Victoria

### Pole Crítica
```
💎 POLE CRÍTICA

@Usuario primer mensaje del día tío
⏱️ 12:00:03

💰 +20 pts | 🔥 racha: 12 días
🎯 total: 28 pts (con multiplicador)

imparable 🔥
```

### Pole Secundón
```
🥈 SECUNDÓN

@Usuario segundo del día
⏱️ 12:00:08

💰 +11 pts | 🔥 racha: 5 días
🎯 total: 13.2 pts

bien jugado 👏
```

### Pole Normal
```
🏁 POLE

@Usuario
⏱️ 12:05:30

💰 +10 pts | 🔥 racha: 5 días
🎯 total: 11 pts

así se hace 🤝
```

### Pole Marranero
```
🐷 POLE MARRANERO

@Usuario llegaste tarde hermano
⏱️ 13:20:00

💰 +7 pts
🎯 total: 7 pts

mañana madruga más 🥱
```

### Pole Perfecta (12:00:00)
```
🤯 @Usuario

ESPERA ESPERA
12:00:00 EXACTAS???

hermano eso es ARTE
+[X] pts + bonus perfección

LEYENDA 👑
```

---

## Easter Eggs y Mensajes Especiales

### Cuando alguien llega tarde
```
😴 @Usuario tío son las 3 de la tarde
   @Winner ganó hace 3 horas ya te vale
   mañana madruga más 🥱
```

```
🐌 @Usuario menuda tortuga
   @Winner te ha pasado por encima
   ponte las pilas hermano
```

### Cuando alguien rompe su récord personal
```
🎉 @Usuario nuevo récord personal

antes: 45 días de racha
ahora: 46 días

así se hace tío sigue así 🔥
```

### Cuando alguien pierde una racha larga
```
💔 @Usuario

se acabó tu racha de 67 días hermano
duele lo sé pero conservas el 20% (13 pts)

67 días es una barbaridad tío
descansa y vuelve más fuerte 💪
```

### Empate técnico (diferencia <0.1s)
```
⚡ foto finish entre @Usuario1 y @Usuario2

diferencia: 0.03 segundos
ganador: @Usuario1

@Usuario2 tío estuviste a NADA
la próxima es tuya 🤝
```

### Si es viernes
```
🎉 VIERNES BABY

hoy el pole vale el doble
porque sí porque me da la gana

que tengáis buen finde chat 🔥
```

### Si alguien gana 10 días seguidos
```
🔥 @Usuario lleva 10 días seguidos ganando

esto ya es personal tío
quien lo tumbe mañana se lleva +15 puntos bonus

a por él chat 😈
```

### Si nadie ha ganado en 5 minutos
```
⏰ hermano ya pasaron 5 minutos

¿nadie quiere el pole o qué?
está ahí tirado esperando 💀
```

### Si alguien intenta hacer pole a las 11:59
```
🤨 @Usuario son las 11:59

casi casi pero no
espera 1 minuto más genio
```

### Batalla campal (3+ en primeros 2s)
```
⚡ BATALLA CAMPAL

@Usuario1, @Usuario2 y @Usuario3 en 2 segundos
esto es el salvaje oeste hermano

ganador: @Usuario1 por 0.001s
los demás lloran 😭
```

### Si alguien gana justo después de ser mencionado
```
👀 @Usuario1: "no voy a ganar hoy"
[2 segundos después]
@Usuario1: pole

TÍO
acabas de mentir a toda la comunidad
pero ganaste así que todo bien 🤝
```

### Si alguien lleva 100 días sin ganar
```
💀 @Usuario hace 100 días que no ganas

hermano
100 DÍAS

¿estás bien? ¿necesitas ayuda?
mañana lo intentas a las 11:59:58 y ya está
```

### Si alguien pierde por 0.001 segundos
```
😬 @Usuario perdiste por 0.001 segundos

literalmente parpadeaste
eso es todo
un parpadeo entre tú y la gloria

F en el chat 💀
```

### Detección de macro (sospecha)
```
🤨 @Usuario

10 poles perfectas seguidas a las 12:00:00
siempre 12:00:00.000

o eres un dios
o tienes un script

admin revisa esto porfa
```

### Vuelta de suspensión
```
🔄 @Usuario ha vuelto de su time-out

24 horas de reflexión
esperemos que hayas aprendido

segunda oportunidad tío
no la cagues 🤝
```

### Cuando el bot se reinicia
```
👋 buenas chat he vuelto

preparaos que en [X minutos] abrimos pole
el que pestañea pierde 👁️
```

### Si alguien hace pole a las 6:66
```
🤨 @Usuario son las 6:66

espera
eso ni existe tío

cómo has...? sabes qué da igual
+10 puntos por confundirme
```

---

## Configuración de Notificaciones

```
/notify reset on/off          # Avisar cuando se abre pole
/notify winner on/off         # Avisar cuando alguien gana
/notify mention @role         # Mencionar rol específico
```
