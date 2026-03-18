# Reglas Oficiales - Pole Bot

## Objetivo

Ser de los primeros en escribir `pole` cuando el bot abra el dia.

## Como funciona cada dia

1. El bot genera una hora aleatoria de apertura por servidor.
2. Cuando llega la hora, envia la notificacion en el canal configurado.
3. Los usuarios escriben `pole` y el bot clasifica la velocidad.

## Categorias y puntos base

- Critica (0-10 min): 20 pts
- Veloz (10 min-3h): 15 pts
- Normal (3h-00:00): 10 pts
- Marranero (dia siguiente): 5 pts

Los puntos finales aplican multiplicador de racha.

## Cuotas

Las cuotas premium se calculan sobre jugadores activos del servidor:

- Critica: 10%
- Veloz: 30%

Si la cuota de una categoria se llena, baja a la siguiente sin bloquear el pole.

## Regla global clave

Solo una pole por dia a nivel global (entre todos los servidores).

Si ya hiciste pole en otro servidor, no puedes repetir ese mismo dia.

## Rachas

- La racha es global (no por servidor).
- Si cumples el dia, sube +1.
- Si no cumples, puede resetearse a 0.
- El marranero sirve para recuperar el dia anterior dentro de su ventana.

## Sobre el marranero

- No es una segunda pole del mismo dia.
- Cuenta para el dia anterior (`pole_date` del dia perdido).
- Si ya hiciste pole ese dia (en cualquier servidor), no puedes usar marranero para duplicar.

## Casos de downtime

El bot tiene failsafes de notificacion y verificaciones de estado para reducir perdidas por caidas.

En incidencias reales, los admins con debug pueden usar comandos de compensacion:

- `/debug compensate_downtime`
- `/debug restore_streak`
- `/debug restore_guild`

## Configuracion minima por servidor

Con `/settings`:

- Canal de pole
- Rango horario
- Notificaciones
- Ping de rol o everyone (opcional)
- Idioma

## FAQ corta

- "Es por mayusculas?": No, `pole` se valida ignorando mayusculas/minusculas.
- "Puedo polear en dos servers?": No, una pole diaria global.
- "Perdi racha por bug": Reporta fecha/guild y usa comando debug de restauracion si procede.
