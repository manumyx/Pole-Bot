# 🏁 Pole Bot

Bot de Discord para competiciones diarias de "pole position" con sistema de puntos, rachas y logros.

## 📋 Características

- **Sistema de Pole Diario**: Los usuarios compiten por ser los primeros en escribir cada día a las 12:00h
- **Categorías de Pole**:
  - 💎 **Crítica** (20 pts): Primer mensaje del día
  - 🥈 **Secundón** (11 pts): Segundo mensaje del día
  - 🏁 **Normal** (10 pts): Pole entre 12:00 y 13:00
  - 🐷 **Marranero** (7 pts): Pole después de las 13:00
- **Sistema de Rachas**: Multiplicadores de hasta 2.5× por días consecutivos (máx. 365 días)
- **Logros**: Más de 20 logros públicos y 15 logros ocultos por descubrir
- **Rangos Progresivos**: Desde Novato (0 pts) hasta Inmortal (50K+ pts)
- **Anti-Trampas**: Detección de bots, macros y spam
- **Sistema de Strikes**: Penalizaciones progresivas (3 strikes = 24h ban del comando)

## 🚀 Instalación

### Requisitos
- Python 3.8+
- discord.py >= 2.3.0
- Base de datos SQLite3

### Setup
```bash
# Clonar el repositorio
git clone https://github.com/manumyx/pole-bot.git
cd pole-bot

# Instalar dependencias
pip install -r requirements.txt

# Configurar el bot
cp config.json.example config.json
# Editar config.json con tu token de Discord

# Ejecutar el bot
python main.py
```

## 📚 Documentación

- **[DESIGN.md](docs/DESIGN.md)**: Documento de diseño completo (referencia técnica)
- **[RULES.md](docs/RULES.md)**: Reglas del pole, validaciones y penalizaciones
- **[SCORING.md](docs/SCORING.md)**: Sistema de puntos, rachas y rangos
- **[ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md)**: Todos los logros (públicos y ocultos)
- **[COMMANDS.md](docs/COMMANDS.md)**: Referencia de comandos y configuración
- **[NOTIFICATIONS.md](docs/NOTIFICATIONS.md)**: Personalidad del bot y mensajes

## 🎮 Comandos Básicos

### Usuarios
```
/pole              # Intentar hacer pole
/stats             # Ver tus estadísticas
/leaderboard       # Ver ranking global
/achievements      # Ver tus logros
```

### Administradores
```
/polereset         # Forzar reset del pole
/polestrike @user  # Añadir strike a un usuario
/poleping @role    # Configurar rol de notificaciones
```

## 🏆 Sistema de Puntos

```
Puntos Finales = Puntos Base × Multiplicador de Racha
```

**Puntos Base:**
- Crítica: 20 pts
- Secundón: 11 pts
- Normal: 10 pts
- Marranero: 7 pts

**Multiplicadores de Racha:**
- 1 día: 1.0× (sin bonus)
- 30 días: 1.5×
- 100 días: 2.0×
- 300+ días: 2.5× (máximo)

*No se redondean los decimales (11 × 1.2 = 13.2 pts)*

## 🎯 Logros Destacados

- 🔥 **El Imparable**: 30 días de racha consecutiva
- 💎 **Crítico en Serie**: 10 poles críticas seguidas
- 🌙 **Vampiro**: 10 poles entre 00:00 y 06:00
- 🤯 **¿?¿?¿?**: Pole exacta a las 12:00:00.000
- 👑 **Rey del Pole**: 100 victorias totales
- *Y 15 logros ocultos por descubrir...*

## 🛡️ Sistema Anti-Trampas

- Detección de bots (CAPTCHA si es necesario)
- Anti-spam (1 intento por minuto)
- Anti-macros (detección de patrones sospechosos)
- Sistema de strikes progresivo

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).

Eres libre de compartir y adaptar este proyecto, siempre que des crédito apropiado y distribuyas tus contribuciones bajo la misma licencia.

## 📧 Contacto

Si tienes preguntas o sugerencias, abre un issue en GitHub.

---

**Estado del Proyecto**: 🟡 En desarrollo (v1.0)  
**Última Actualización**: Enero 2025
