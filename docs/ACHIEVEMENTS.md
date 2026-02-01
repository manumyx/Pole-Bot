# 🏅 Sistema de Logros

⚠️ **ATENCIÓN: SISTEMA NO IMPLEMENTADO** ⚠️

Este documento contiene el diseño original del sistema de logros que **NO está implementado actualmente** en el bot.

El sistema actual utiliza **Badges de Temporada** en lugar de logros individuales.

---

## 💎 Sistema Actual: Badges de Temporada

El bot implementa un sistema de 6 niveles de badges basados en puntos de temporada:

| Badge | Puntos Requeridos | Descripción |
|-------|-------------------|-------------|
| 🥉 Bronce | 0 pts | Participante |
| 🥈 Plata | 500 pts | Constante |
| 🥇 Oro | 1,500 pts | Dedicado |
| 💎 Diamante | 3,500 pts | Experto |
| 💜 Amatista | 6,000 pts | Élite |
| ❤️ Rubí | 9,000 pts | Leyenda |

**Ver más**: Consulta `SCORING.md` y `SEASON_MIGRATION.md` para detalles del sistema de temporadas.

---

## ⚠️ Lo que sigue son diseños NO IMPLEMENTADOS

Todo lo que aparece a continuación es contenido de diseño que **no funciona actualmente** en el bot.

Si deseas implementar el sistema de logros, este documento puede servir como referencia de diseño.

---

## Logros Básicos (NO IMPLEMENTADO)
- 🏁 **Primera Sangre** - Tu primer pole
- 🌟 **10 Poles** - Alcanza 10 poles totales
- 💫 **50 Poles** - Alcanza 50 poles totales
- ⭐ **100 Poles** - Alcanza 100 poles totales
- 👑 **500 Poles** - Leyenda absoluta

## Logros de Poles Críticas
- 💎 **Cazador de Críticas** - 10 poles críticas
- 💎💎 **Maestro de Críticas** - 50 poles críticas
- 💎💎💎 **Dios de las Críticas** - 100 poles críticas
- ⏰ **Perfección Absoluta** - Pole a las 12:00:00 exactas
- ⚡ **Rayo** - 10 poles en primeros 3 segundos
>
## Logros de Rachas
- 🔥 **En Racha** - 3 días consecutivos
- 🔥🔥 **Semana Perfecta** - 7 días consecutivos
- 🔥🔥🔥 **Mes Imparable** - 30 días consecutivos
- 👑 **Centurión** - 100 días consecutivos
- 💎 **Inmortal** - 365 días consecutivos

## Logros Especiales (Difíciles)
- 🌅 **Friki total** - 10 poles en los primeros 2 segundos
- 🎯 **Precisión Láser** - 20 poles críticas seguidas
- 🛡️ **Defensor Invicto** - 30 días seguidos en tu servidor
- 💀 **Asesino de Récords** - Rompe 50 récords personales
- 🌟 **Leyenda** - Top 3 global por 30 días

## Logros de Puntos Totales

Se desbloquean al alcanzar puntos acumulados. Nombres tentativos:

| Puntos | Nombre | Descripción | Rareza |
|--------|--------|-------------|--------|
| 10 | El Comienzo | Primeros pasos en el camino del pole | 95% |
| 100 | Persistente | Ya no fue suerte: sigues aquí | 80% |
| 1,000 | Umbral Experto | Empiezas a ser reconocido | 50% |
| 10,000 | Camino del Maestro | Demuestras constancia real | 25% |
| 100,000 | Maestro del Pole | Dominio avanzado | 10% |
| 1,000,000 | Ascenso Divino | ¿Leyenda? Te acercas a la mitología | 1% |
| 10,000,000 | Nuevo Dios | Estás en otra liga | 0.1% |
| 100,000,000 | Entidad Superior | Más concepto que jugador | 0.01% |

**Nota:** Los porcentajes se calculan dinámicamente en producción:
`porcentaje = jugadores_con_logro / jugadores_activos * 100`

**⚠️ SISTEMA NO IMPLEMENTADO - Los badges de temporada reemplazan este sistema**

### Visualización (NO IMPLEMENTADO)

```
🏆 LOGRO DESBLOQUEADO: "Maestro del Pole"
Puntos totales: 100,000
Solo el 9.4% de los jugadores han llegado aquí.
```

---

## 🌚 Logros Ocultos (No se muestran hasta conseguirlos)

- 👻 **Fantasma** - Ganar después de 30 días sin participar
- 🔍 **Dataminer** - Descubrir y escribir el texto secreto oculto en el código (definido por admin)
- 🎯 **Explorador** - Encontrar 3 easter eggs ocultos del bot
- 🏎️ **EL NANO?????????** - Hacer pole exactamente a las 3:33 (hora del Fernando Alonso hermano)
- 🌚 **Insomnio Crónico** - Hacer pole 7 días seguidos entre las 3:00 y 5:00 AM
- 🎰 **Apostador** - Hacer pole exactamente a las 7:77... espera eso no existe, hazlo a las 7:07
- 🤡 **Payaso Oficial** - Perder 10 poles por intentarlo antes de las 12h (y seguir intentándolo)
- ⚰️ **Muerto por Dentro** - Llegar segundo 20 veces (tan cerca y tan lejos tío)
- 🐌 **Récord Mundial** - Ser el último en hacer pole del día 15 veces (premio al más lento)


---

## 💬 Mensajes de Logros Desbloqueados

### EL NANO?????????
```
🏎️ @Usuario acaba de desbloquear: EL NANO?????????

3:33 DE LA MAÑANA TÍO
literalmente la hora del Fernando Alonso

esto es arte hermano
[Embed: GIF del nano con el casco]
```

### Muerto por Dentro
```
⚰️ @Usuario ha desbloqueado: Muerto por Dentro

20 veces segundo
20 VECES

hermano en algún momento tienes que plantearte cosas
pero hey al menos eres constante 💀
```

### Payaso Oficial
```
🤡 @Usuario nuevo logro: Payaso Oficial


y sigues aquí dándole

no sé si eres valiente o directamente no aprendes
pero respeto la dedicación tío 🎪
```
