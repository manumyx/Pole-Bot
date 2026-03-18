# Badges y Rangos

Este documento describe el sistema que SI esta implementado en Pole Bot.

## Sistema actual

El progreso competitivo se apoya en:

- Puntos de temporada
- Rangos visuales por puntos
- Badges permanentes por posicion final

## Rangos por puntos de temporada

- Bronce
- Plata
- Oro
- Diamante
- Amatista
- Rubi

Los umbrales exactos se gestionan desde `utils/scoring.py`.

## Badges permanentes

Al cerrar temporada se guardan resultados y se asignan badges por posicion final.

Top 3 de temporada:

- 1o
- 2o
- 3o

Estos badges se conservan historicamente.

## POLE REWIND

En cambio de temporada, el bot puede publicar resumen de hall of fame local/global.

## Importante

Este repo NO mantiene un sistema de "achievements individuales" tipo desbloqueables por hitos (ejemplo: "10 criticas", "100 poles", etc.) como parte activa del producto.

Si se implementa en el futuro, este documento se ampliara con reglas, triggers y persistencia.
