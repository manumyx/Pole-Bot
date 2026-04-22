---
name: revisor-logica-juego-pole-bot
description: "Usa esta skill para auditar la logica del juego de pole: validaciones de participacion, calculo de puntos, marraneros e i18n sin textos hardcodeados."
---

# Skill: Revisor de Logica de Juego (Pole-Bot)

## Mision

Asegurar que las reglas del juego de la pole sean sagradas y no tengan agujeros.

## Checklist de Revision

1. **Doble Participacion:** Comprueba que se valida si el usuario ya ha hecho pole hoy **antes** de procesar el intento.
2. **Calculo de Puntos:** Verifica que la asignacion de puntos usa `utils/scoring.py` y no logica duplicada.
3. **Marraneros:** Revisa que se detecte correctamente cuando alguien intenta hacer pole antes de tiempo.
4. **Mensajes:** Confirma que todos los mensajes de respuesta pasan por `t()` de `utils/i18n.py` y no hay textos hardcodeados.
