# 📜 Reglas del Pole Bot v1.0

Documento oficial de las reglas del juego.

---

## 🎯 Objetivo del Juego

Ser el más rápido en escribir **"pole"** cuando el bot anuncie la apertura diaria. Acumula puntos, mantén rachas y compite por el ranking de la temporada.

---

## 🕐 Funcionamiento Básico

### 1. Apertura Diaria
- Cada día el bot genera una **hora aleatoria** de apertura
- La hora está dentro del rango configurado por el servidor (ej: 12:00-20:00)
- El bot garantiza al menos **4 horas** de diferencia con el día anterior
- Se envía una **notificación automática** cuando se abre

### 2. Cómo Participar
1. Espera la notificación de apertura (embed verde con 🔔)
2. Ve al canal configurado
3. Escribe **exactamente** la palabra: `pole`
4. ¡Recibirás tus puntos instantáneamente!

### 3. Validación
- ✅ Palabra exacta: `pole` (minúsculas/mayúsculas no importan)
- ❌ No válido: `pol`, `poles`, `mi pole`, `pole!`
- ✅ Solo en el canal configurado
- ✅ Solo después de la apertura
- ✅ Una vez por día por usuario

---

## ⚡ Sistema de Categorías

Los puntos que ganas dependen de **qué tan rápido** respondas:

| Categoría | Tiempo | Puntos Base | Cuota | Emoji |
|-----------|--------|-------------|-------|-------|
| **CRÍTICA** | 0-10 min | 20 pts | 10% del servidor | 🏆 |
| **VELOZ** | 10 min-3h | 15 pts | 30% del servidor | ⚡ |
| **POLE** | 3h-00:00 | 10 pts | Ilimitado | 🎯 |
| **MARRANERO** | Después 00:00 | 5 pts | Ilimitado | 🐷 |

### Sistema de Cuotas
Las categorías premium tienen límites:
- **Crítica**: Solo el 10% de los miembros del servidor puede reclamarla
- **Veloz**: Solo el 30% puede reclamarla

**Ejemplo:** En un servidor de 100 miembros:
- Solo 10 personas pueden conseguir Crítica
- Solo 30 pueden conseguir Veloz
- El resto obtendrá Pole (normal)

Si llegas en 8 minutos pero ya hay 10 Críticas, se degrada automáticamente a Veloz.

---

## 🔥 Sistema de Rachas

### ¿Qué es una Racha?
Días **consecutivos** haciendo pole. Cada día que haces pole:
- ✅ Tu racha aumenta en +1
- 📈 Tu multiplicador de puntos aumenta
- 🏆 Más puntos por cada pole

### Multiplicadores Progresivos

| Días | Multiplicador | Ejemplo (20 pts base) |
|------|---------------|----------------------|
| 1 día | x1.0 | 20.0 pts |
| 7 días | x1.1 | 22.0 pts |
| 14 días | x1.2 | 24.0 pts |
| 30 días | x1.4 | 28.0 pts |
| 60 días | x1.6 | 32.0 pts |
| 90 días | x1.8 | 36.0 pts |
| 180 días | x2.1 | 42.0 pts |
| 300 días | x2.5 | **50.0 pts** |
| 365 días | x2.5 | 50.0 pts (máximo) |

### Cómo Perder tu Racha
- ❌ No hacer pole un día completo
- ❌ Se resetea a 0 y pierdes el multiplicador
- ✅ Recibirás notificación en el resumen de medianoche

### Protección de Racha
- El sistema garantiza **4 horas mínimo** entre poles
- Ejemplo: Si ayer abrió a las 23:00, hoy no abrirá antes de las 03:00
- Esto te da tiempo suficiente para mantener tu racha

---

## 🚫 Restricciones

### Una Pole por Día (Global)
- Solo puedes hacer **una pole al día** en CUALQUIER servidor
- Si ya hiciste pole en el servidor A, no podrás en el servidor B el mismo día
- Esto previene spam y mantiene la competencia justa

**Mensaje de error:**
```
❌ Sólo puedes hacer una pole al día a nivel global.
Ya hiciste pole hoy en: Servidor XYZ
```

### Antes de Apertura
Si escribes `pole` antes de la hora de apertura:
- ⚠️ Se añade reacción de advertencia
- 💬 Mensaje: "⏳ Aún no ha abierto. Espera al aviso."
- ❌ No cuenta como pole

### Duplicado en el Mismo Servidor
Si escribes `pole` múltiples veces el mismo día en el mismo servidor:
- 🔇 El bot ignora los intentos adicionales
- ❌ No hay penalización
- ℹ️ No se muestra mensaje (para no hacer spam)

---

## 🎖️ Rangos y Badges

### Rangos por Puntos (Temporada Actual)
Tu rango se determina por tus puntos en la temporada actual:

| Rango | Badge | Puntos Necesarios |
|-------|-------|-------------------|
| Rubí Maestro | 💎 | 2000+ pts |
| Amatista Élite | 🔮 | 1500+ pts |
| Diamante Supremo | 💎 | 1000+ pts |
| Oro Imperial | 🥇 | 600+ pts |
| Plata Distinguida | 🥈 | 300+ pts |
| Bronce Valiente | 🥉 | 100+ pts |

### Badges de Temporada (Permanentes)
Al finalizar una temporada, los Top 3 reciben badges permanentes:
- 🥇 **1er Lugar**: Campeón de [Temporada]
- 🥈 **2do Lugar**: Subcampeón de [Temporada]
- 🥉 **3er Lugar**: Finalista de [Temporada]

Estos badges se muestran en tu perfil para siempre.

---

## 🏆 Sistema de Temporadas

### Duración
- **1 año completo**: 1 de enero - 31 de diciembre
- Migración automática a las 00:00 del 1 de enero

### Al Finalizar una Temporada
1. 📊 Se guardan las posiciones finales
2. 🎖️ Se otorgan badges permanentes a Top 3
3. 📜 Todo queda registrado en el historial
4. 🔄 Se resetean puntos de temporada
5. 🔥 Se resetean rachas a 0
6. ✅ Estadísticas lifetime se mantienen

### Tipos de Estadísticas
- **Temporada Actual**: Puntos de la temporada en curso
- **Lifetime (Carrera)**: Suma de todas las temporadas históricas
- **Historial**: Consultar temporadas finalizadas

---

## 🌐 Multi-Servidor

### Representación de Servidor
- Al hacer tu primera pole global, automáticamente representas ese servidor
- Tu elección es permanente
- Tus puntos cuentan para el ranking global de ese servidor

### Rankings
- **Local**: Usuarios del servidor (sin importar a quién representen)
- **Global**: Todos los usuarios del bot
- **Servidores**: Competencia entre servidores (suma de puntos de representantes)

---

## 📅 Eventos Especiales

### Resumen de Medianoche (00:00)
Cada día a medianoche el bot envía un resumen:
- 🏆 Quién ganó el pole del día anterior
- 💔 Quién perdió su racha
- 📢 Anuncia el nuevo día

### Pole Marranero
Si no conseguiste hacer pole antes de las 00:00:
- 🐷 Puedes hacerlo después de medianoche
- ⚠️ Solo obtienes 5 puntos base
- ✅ Pero mantienes tu racha (no se pierde)
- 📝 Cuenta como pole del día anterior

---

## ⚙️ Configuración del Servidor

Solo administradores pueden configurar:

### Comando `/settings`
Menú interactivo con opciones:

1. **📺 Canal de Pole**
   - Canal donde se envían notificaciones
   - Canal donde se acepta la palabra "pole"

2. **🕐 Rango Horario**
   - Hora mínima y máxima para apertura
   - Ejemplo: 12:00 - 20:00

3. **🔔 Notificaciones**
   - Activar/desactivar notificación de apertura
   - Activar/desactivar resumen de medianoche

4. **👥 Ping de Rol**
   - Sin ping / Ping a rol específico / @everyone
   - Útil para asegurar que todos vean la apertura

---

## 🚨 Casos Especiales

### Cambio de Hora del Servidor
Si un admin cambia el rango horario:
- ✅ Toma efecto al día siguiente
- ℹ️ El pole del día actual mantiene su hora original

### Bot Offline
Si el bot estuvo offline durante la hora de apertura:
- ⚠️ No se genera pole ese día
- ❌ Los usuarios pierden su racha
- 📝 Considera usar hosting confiable 24/7

### Días sin Pole
Si un servidor no tiene pole configurado:
- ❌ Los usuarios de ese servidor no pueden participar
- ℹ️ Pueden participar en otros servidores donde esté configurado

---

## ❓ Preguntas Frecuentes

**¿Puedo cambiar de servidor representado?**
- No, la elección es permanente al hacer tu primera pole global.

**¿Qué pasa si pierdo un día?**
- Pierdes tu racha y vuelve a 0. Debes empezar de nuevo.

**¿Los puntos lifetime se resetean?**
- No, solo se resetean los puntos de temporada. Lifetime es permanente.

**¿Puedo hacer pole en múltiples servidores?**
- Solo una pole al día en total, no importa en cuántos servidores estés.

**¿Cómo sé mi ranking?**
- Usa `/profile` para ver tus stats o `/leaderboard` para el ranking.

**¿El pole marranero cuenta para la racha?**
- Sí, pero solo otorga 5 puntos base.

---

## 📞 Soporte

Si tienes dudas sobre las reglas, usa:
- `/polehelp` - Tutorial interactivo
- Contacta a un administrador del servidor
- Reporta bugs en el repositorio de GitHub

---

**Versión:** 1.0  
**Última actualización:** Diciembre 2024
