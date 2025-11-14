"""
Utilidad para manejar la base de datos (persistencia de datos)
Usa archivos JSON para guardar información del bot
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class Database:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.pole_file = os.path.join(data_dir, "pole_data.json")
        
        # Crear directorio si no existe
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"📁 Directorio de datos creado: {data_dir}")
        
        # Cargar o crear archivo de datos
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """Cargar datos desde el archivo JSON"""
        if os.path.exists(self.pole_file):
            try:
                with open(self.pole_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error cargando datos: {e}")
                return self._create_default_data()
        else:
            return self._create_default_data()
    
    def _create_default_data(self) -> Dict[str, Any]:
        """Crear estructura de datos por defecto"""
        return {
            "servers": {},  # Datos por servidor
            "last_save": None
        }
    
    def _save_data(self):
        """Guardar datos en el archivo JSON"""
        try:
            self.data["last_save"] = datetime.now().isoformat()
            with open(self.pole_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando datos: {e}")
    
    def get_server_data(self, server_id: int) -> Dict[str, Any]:
        """Obtener datos de un servidor específico"""
        server_id = str(server_id)
        
        if server_id not in self.data["servers"]:
            self.data["servers"][server_id] = {
                "pole_channel_id": None,
                "last_pole_date": None,
                "last_pole_winner": None,
                "pole_history": [],  # Lista de ganadores históricos
                "penalties": []      # Lista de penalties
            }
            self._save_data()
        
        return self.data["servers"][server_id]
    
    def save_pole_winner(self, server_id: int, user_id: int, username: str, 
                        channel_id: int, timestamp: str):
        """Guardar el ganador de la pole"""
        server_data = self.get_server_data(server_id)
        
        server_data["last_pole_date"] = timestamp
        server_data["last_pole_winner"] = {
            "user_id": user_id,
            "username": username,
            "timestamp": timestamp,
            "channel_id": channel_id
        }
        
        # Agregar al historial
        server_data["pole_history"].append({
            "user_id": user_id,
            "username": username,
            "timestamp": timestamp,
            "channel_id": channel_id
        })
        
        self._save_data()
    
    def add_penalty(self, server_id: int, user_id: int, username: str, 
                   reason: str, timestamp: str):
        """Agregar una penalty"""
        server_data = self.get_server_data(server_id)
        
        server_data["penalties"].append({
            "user_id": user_id,
            "username": username,
            "reason": reason,
            "timestamp": timestamp
        })
        
        self._save_data()
    
    def set_pole_channel(self, server_id: int, channel_id: int):
        """Establecer el canal de pole para un servidor"""
        server_data = self.get_server_data(server_id)
        server_data["pole_channel_id"] = channel_id
        self._save_data()
    
    def get_pole_stats(self, server_id: int) -> Dict[str, Any]:
        """Obtener estadísticas de poles de un servidor"""
        server_data = self.get_server_data(server_id)
        
        # Contar poles por usuario
        pole_counts = {}
        for pole in server_data["pole_history"]:
            user_id = pole["user_id"]
            if user_id not in pole_counts:
                pole_counts[user_id] = {
                    "count": 0,
                    "username": pole["username"]
                }
            pole_counts[user_id]["count"] += 1
        
        # Ordenar por cantidad de poles
        sorted_stats = sorted(
            pole_counts.items(), 
            key=lambda x: x[1]["count"], 
            reverse=True
        )
        
        return {
            "total_poles": len(server_data["pole_history"]),
            "total_penalties": len(server_data["penalties"]),
            "top_polers": sorted_stats[:10],  # Top 10
            "last_winner": server_data.get("last_pole_winner")
        }
