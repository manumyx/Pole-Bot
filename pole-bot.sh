#!/bin/bash

################################################################################
# Pole Bot - Script de Gestión AIO para Linux Debian/Ubuntu
# 
# Este script proporciona una interfaz completa para:
# - Instalar dependencias (Python 3.10+, venv, etc.)
# - Crear y gestionar entorno virtual
# - Iniciar/detener el bot
# - Ver logs y estado
# - Configurar inicio automático con systemd
#
# Uso: ./pole-bot.sh [comando]
# Comandos disponibles: install, start, stop, restart, status, logs, enable, disable
################################################################################

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorios y archivos
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR"
VENV_DIR="$BOT_DIR/.venv"
MAIN_FILE="$BOT_DIR/main.py"
ENV_FILE="$BOT_DIR/.env"
PID_FILE="$BOT_DIR/.bot.pid"
LOG_FILE="$BOT_DIR/bot.log"
SERVICE_NAME="pole-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

################################################################################
# Funciones de Utilidad
################################################################################

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Este comando requiere permisos de root (sudo)"
        exit 1
    fi
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        return 1
    fi
    
    # Verificar versión mínima (3.10)
    python_version=$(python3 --version | cut -d' ' -f2)
    required_version="3.10"
    
    if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
        return 1
    fi
    
    return 0
}

################################################################################
# Comando: install
# Instala todas las dependencias necesarias y configura el entorno
################################################################################

cmd_install() {
    print_header "Instalando Pole Bot"
    
    # Detectar si es Raspberry Pi
    IS_RPI=false
    if [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model; then
        IS_RPI=true
        print_info "Detectado: Raspberry Pi"
    fi
    
    # Verificar si es root para instalar paquetes del sistema
    if [ "$EUID" -ne 0 ]; then
        print_warning "Algunas instalaciones requieren sudo. Usa 'sudo ./pole-bot.sh install'"
        print_info "Intentando instalación sin sudo (solo venv y dependencias Python)..."
    else
        # Actualizar repositorios
        print_info "Actualizando repositorios..."
        apt-get update -qq
        
        # Instalar Python 3 y venv
        if $IS_RPI; then
            # Raspberry Pi - usar Python del sistema
            print_info "Instalando Python 3 (Raspberry Pi)..."
            apt-get install -y python3 python3-venv python3-pip python3-dev
            print_success "Python instalado desde repositorios de Raspberry Pi OS"
        else
            # Ubuntu/Debian regular
            if ! check_python; then
                print_info "Instalando Python 3.10+..."
                apt-get install -y software-properties-common
                add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || {
                    print_warning "No se pudo añadir PPA, usando Python del sistema"
                    apt-get install -y python3 python3-venv python3-pip python3-dev
                }
                apt-get update -qq
                apt-get install -y python3.10 python3.10-venv python3.10-dev 2>/dev/null || \
                    apt-get install -y python3 python3-venv python3-pip python3-dev
                print_success "Python instalado"
            else
                print_success "Python 3.10+ ya instalado"
            fi
        fi
        
        # Instalar pip si no está
        if ! command -v pip3 &> /dev/null; then
            print_info "Instalando pip..."
            apt-get install -y python3-pip
            print_success "pip instalado"
        else
            print_success "pip ya instalado"
        fi
    fi
    
    # Verificar que Python 3 está disponible (relajar requisito de versión)
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 no está instalado. Instálalo manualmente:"
        echo "  sudo apt-get install python3 python3-venv python3-pip"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION detectado"
    
    # Crear entorno virtual si no existe
    if [ ! -d "$VENV_DIR" ]; then
        print_info "Creando entorno virtual..."
        python3 -m venv "$VENV_DIR"
        print_success "Entorno virtual creado en $VENV_DIR"
    else
        print_success "Entorno virtual ya existe"
    fi
    
    # Activar entorno virtual e instalar dependencias
    print_info "Instalando dependencias Python..."
    source "$VENV_DIR/bin/activate"
    
    if [ -f "$BOT_DIR/requirements.txt" ]; then
        pip install --upgrade pip -q
        pip install -r "$BOT_DIR/requirements.txt" -q
        print_success "Dependencias instaladas"
    else
        print_error "No se encontró requirements.txt"
        exit 1
    fi
    
    # Verificar archivo .env
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "No se encontró archivo .env"
        print_info "Crea uno con:"
        echo "  cp .env.example .env"
        echo "  nano .env"
        echo ""
        print_info "Variables requeridas:"
        echo "  DISCORD_TOKEN=tu_token_aqui"
        echo "  DISCORD_CLIENT_ID=tu_client_id"
    else
        print_success "Archivo .env encontrado"
    fi
    
    # Crear directorio de datos si no existe
    mkdir -p "$BOT_DIR/data"
    
    print_success "Instalación completada"
    echo ""
    print_info "Próximos pasos:"
    echo "  1. Configura .env con tu token de Discord"
    echo "  2. Inicia el bot: ./pole-bot.sh start"
    echo "  3. (Opcional) Habilita inicio automático: sudo ./pole-bot.sh enable"
}

################################################################################
# Comando: start
# Inicia el bot en segundo plano
################################################################################

cmd_start() {
    print_header "Iniciando Pole Bot"
    
    # Verificar si ya está corriendo
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        print_warning "El bot ya está corriendo (PID: $(cat $PID_FILE))"
        exit 0
    fi
    
    # Verificar entorno virtual
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Entorno virtual no encontrado. Ejecuta primero: ./pole-bot.sh install"
        exit 1
    fi
    
    # Verificar .env
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Archivo .env no encontrado. Configúralo antes de iniciar."
        exit 1
    fi
    
    # Iniciar bot en segundo plano
    print_info "Iniciando bot..."
    source "$VENV_DIR/bin/activate"
    nohup python3 "$MAIN_FILE" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    
    # Verificar que inició correctamente
    if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        print_success "Bot iniciado (PID: $(cat $PID_FILE))"
        print_info "Ver logs: ./pole-bot.sh logs"
    else
        print_error "El bot falló al iniciar. Revisa los logs:"
        tail -n 20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

################################################################################
# Comando: stop
# Detiene el bot
################################################################################

cmd_stop() {
    print_header "Deteniendo Pole Bot"
    
    if [ ! -f "$PID_FILE" ]; then
        print_warning "El bot no está corriendo (no se encontró PID)"
        exit 0
    fi
    
    PID=$(cat "$PID_FILE")
    
    if kill -0 "$PID" 2>/dev/null; then
        print_info "Deteniendo bot (PID: $PID)..."
        kill "$PID"
        sleep 2
        
        # Force kill si no se detuvo
        if kill -0 "$PID" 2>/dev/null; then
            print_warning "Forzando detención..."
            kill -9 "$PID"
        fi
        
        rm -f "$PID_FILE"
        print_success "Bot detenido"
    else
        print_warning "El proceso no está corriendo, limpiando PID..."
        rm -f "$PID_FILE"
    fi
}

################################################################################
# Comando: restart
# Reinicia el bot
################################################################################

cmd_restart() {
    print_header "Reiniciando Pole Bot"
    cmd_stop
    sleep 1
    cmd_start
}

################################################################################
# Comando: status
# Muestra el estado del bot
################################################################################

cmd_status() {
    print_header "Estado de Pole Bot"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            print_success "Bot corriendo (PID: $PID)"
            
            # Mostrar info del proceso
            echo ""
            print_info "Información del proceso:"
            ps -p "$PID" -o pid,ppid,%cpu,%mem,etime,cmd --no-headers
            
            # Mostrar últimas líneas del log
            echo ""
            print_info "Últimas líneas del log:"
            tail -n 10 "$LOG_FILE"
        else
            print_error "Bot detenido (PID obsoleto)"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "Bot detenido"
    fi
    
    # Estado del servicio systemd si está configurado
    if [ -f "$SERVICE_FILE" ]; then
        echo ""
        print_info "Estado del servicio systemd:"
        systemctl status "$SERVICE_NAME" --no-pager 2>/dev/null || true
    fi
}

################################################################################
# Comando: logs
# Muestra los logs del bot
################################################################################

cmd_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        print_warning "No se encontró archivo de logs"
        exit 0
    fi
    
    print_header "Logs de Pole Bot"
    
    # Si se pasa argumento -f, seguir logs en tiempo real
    if [ "$1" = "-f" ] || [ "$1" = "--follow" ]; then
        tail -f "$LOG_FILE"
    else
        # Mostrar últimas 50 líneas
        tail -n 50 "$LOG_FILE"
        echo ""
        print_info "Para seguir logs en tiempo real: ./pole-bot.sh logs -f"
    fi
}

################################################################################
# Comando: enable
# Configura inicio automático con systemd
################################################################################

cmd_enable() {
    check_root
    
    print_header "Configurando Inicio Automático"
    
    # Obtener usuario actual (el que llamó sudo)
    REAL_USER="${SUDO_USER:-$USER}"
    REAL_HOME=$(eval echo ~$REAL_USER)
    
    # Verificar que el venv existe
    if [ ! -f "$VENV_DIR/bin/python3" ]; then
        print_error "Entorno virtual no encontrado en $VENV_DIR"
        print_info "Ejecuta primero: ./pole-bot.sh install"
        exit 1
    fi
    
    # Verificar que main.py existe
    if [ ! -f "$MAIN_FILE" ]; then
        print_error "main.py no encontrado en $MAIN_FILE"
        exit 1
    fi
    
    print_info "Creando servicio systemd..."
    print_info "Usuario: $REAL_USER"
    print_info "Directorio: $BOT_DIR"
    print_info "Python: $VENV_DIR/bin/python3"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Pole Bot - Discord Bot de Competición Diaria
After=network.target

[Service]
Type=simple
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$BOT_DIR
Environment="HOME=$REAL_HOME"
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/python3 $MAIN_FILE
Restart=always
RestartSec=10
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF
    
    print_success "Servicio creado en $SERVICE_FILE"
    
    # Recargar systemd
    print_info "Recargando systemd..."
    systemctl daemon-reload
    
    # Habilitar servicio
    print_info "Habilitando servicio..."
    systemctl enable "$SERVICE_NAME"
    
    print_success "Inicio automático configurado"
    echo ""
    print_info "Comandos útiles:"
    echo "  sudo systemctl start $SERVICE_NAME    # Iniciar servicio"
    echo "  sudo systemctl stop $SERVICE_NAME     # Detener servicio"
    echo "  sudo systemctl restart $SERVICE_NAME  # Reiniciar servicio"
    echo "  sudo systemctl status $SERVICE_NAME   # Ver estado"
    echo "  sudo journalctl -u $SERVICE_NAME -f   # Ver logs"
}

################################################################################
# Comando: disable
# Desactiva inicio automático
################################################################################

cmd_disable() {
    check_root
    
    print_header "Desactivando Inicio Automático"
    
    if [ ! -f "$SERVICE_FILE" ]; then
        print_warning "El servicio no está configurado"
        exit 0
    fi
    
    # Detener servicio si está corriendo
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_info "Deteniendo servicio..."
        systemctl stop "$SERVICE_NAME"
    fi
    
    # Deshabilitar servicio
    print_info "Deshabilitando servicio..."
    systemctl disable "$SERVICE_NAME"
    
    # Eliminar archivo de servicio
    print_info "Eliminando servicio..."
    rm -f "$SERVICE_FILE"
    systemctl daemon-reload
    
    print_success "Inicio automático desactivado"
}

################################################################################
# Menú Principal
################################################################################

show_usage() {
    cat << EOF
${BLUE}Pole Bot - Script de Gestión${NC}

${GREEN}Uso:${NC}
  ./pole-bot.sh [comando]

${GREEN}Comandos disponibles:${NC}
  install   - Instalar dependencias y configurar entorno
  start     - Iniciar el bot en segundo plano
  stop      - Detener el bot
  restart   - Reiniciar el bot
  status    - Mostrar estado del bot
  logs      - Mostrar logs del bot (usa -f para seguir en tiempo real)
  enable    - Configurar inicio automático (requiere sudo)
  disable   - Desactivar inicio automático (requiere sudo)

${GREEN}Ejemplos:${NC}
  ./pole-bot.sh install              # Primera instalación
  ./pole-bot.sh start                # Iniciar bot
  ./pole-bot.sh logs -f              # Ver logs en tiempo real
  sudo ./pole-bot.sh enable          # Habilitar inicio automático

${GREEN}Gestión con systemd (después de enable):${NC}
  sudo systemctl start pole-bot      # Iniciar servicio
  sudo systemctl stop pole-bot       # Detener servicio
  sudo systemctl restart pole-bot    # Reiniciar servicio
  sudo systemctl status pole-bot     # Ver estado
  sudo journalctl -u pole-bot -f     # Ver logs

EOF
}

# Procesar comando
case "${1:-}" in
    install)
        cmd_install
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "${2:-}"
        ;;
    enable)
        cmd_enable
        ;;
    disable)
        cmd_disable
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
