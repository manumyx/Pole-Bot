---
name: experto-persistencia-asincrona-aiosqlite
description: "Usa esta skill cuando tengas que revisar o refactorizar persistencia asíncrona con aiosqlite para evitar bloqueos, cursores abiertos y commits faltantes."
---

# Skill: Experto en Persistencia Asincrona (aiosqlite)

## Contexto
El bot usa `aiosqlite`. Cualquier operacion de base de datos que no sea `await` bloqueara el bot entero.

## Reglas de Oro
- **Consultas:** Usa siempre `async with self.db.get_connection() as conn:`.
- **Transacciones:** Si vas a escribir (INSERT/UPDATE), asegurate de que la funcion sea `async` y tenga `await conn.commit()`.
- **Prevencion de Errores:** Nunca dejes un cursor abierto. Usa siempre el context manager.
- **Tipado:** Los metodos de `database.py` deben devolver tipos claros (`Optional[dict]`, `List[tuple]`, etc.).