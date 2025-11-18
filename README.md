# 🏁 Pole Bot v1.0

[![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

Bot de Discord que implementa competiciones diarias de **pole position** con hora aleatoria, sistema de puntos por velocidad de respuesta, rachas progresivas y temporadas competitivas.

## 🚀 Invitar al Bot

[![Añadir a Discord](https://img.shields.io/badge/Añadir_a_Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1439710236876472482&permissions=277025770560&scope=bot%20applications.commands)

**Permisos necesarios:** Ver canales, Enviar mensajes, Gestionar mensajes, Añadir reacciones, Usar comandos de aplicación, Leer historial

---

## 🎯 Características Principales

### 🎲 Hora Aleatoria Diaria
- El bot genera una **hora diferente cada día** (margen mínimo de 4 horas entre días)
- Notificación automática cuando se abre el pole
- Configuración por servidor con rango horario personalizable

### ⚡ Sistema de Puntos por Velocidad
Cuanto más rápido respondas, más puntos ganas:
- **🏆 CRÍTICA** (0-10 min): 20 pts • Solo 10% del servidor
- **⚡ VELOZ** (10 min-3h): 15 pts • Solo 30% del servidor  
- **🎯 POLE** (3h-00:00): 10 pts • Sin límite
- **🐷 MARRANERO** (después 00:00): 5 pts • Sin límite

### 🔥 Rachas Progresivas
Multiplicadores por días consecutivos (hasta **x2.5** a los 300 días):
- 7 días: x1.1 → 14 días: x1.2 → 30 días: x1.4 → 365 días: x2.5

### 🏆 Sistema de Temporadas
- **Temporadas anuales** con reset automático cada 1 de enero
- Historial completo de temporadas finalizadas
- Badges permanentes por posición final
- Leaderboards por temporada (lifetime, actual, finalizadas)

### 🎖️ Rangos y Badges
Sistema de 6 rangos según puntos de temporada:
- 💎 Rubí (2000+ pts) • 🔮 Amatista (1500+ pts) • 💎 Diamante (1000+ pts)
- 🥇 Oro (600+ pts) • 🥈 Plata (300+ pts) • 🥉 Bronce (100+ pts)

### 🌐 Sistema Multi-Servidor
- Un usuario puede participar en múltiples servidores
- **Una pole por día** a nivel global (previene spam)
- Representación de servidor para competición entre comunidades
- Rankings locales y globales

---