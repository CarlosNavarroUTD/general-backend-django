# apps/citas/services/chat_processor.py
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..utils.date_time_extractor import DateTimeExtractor

class ChatProcessor:
    """
    Procesa conversaciones de chat para extraer fechas y horarios.
    Maneja contexto conversacional entre mensajes.
    """
    
    def __init__(self):
        self.extractor = DateTimeExtractor()
    
    def procesar_chat(self, chat_texto: str) -> Dict:
        """
        Procesa el texto del chat completo y extrae eventos con fechas/horarios.
        
        Args:
            chat_texto: Texto del chat completo (puede contener múltiples líneas)
        
        Returns:
            Diccionario con eventos detectados y metadatos
        """
        # Dividir en mensajes individuales
        mensajes = [msg.strip() for msg in chat_texto.split('\n') if msg.strip()]
        
        eventos = []
        ultima_fecha_completa = None
        ultimo_horario_completo = None
        ultima_fecha_dt = None
        
        for idx, mensaje in enumerate(mensajes):
            # Extraer fechas y horarios del mensaje
            fechas = self.extractor.extraer_fechas(mensaje)
            horarios = self.extractor.extraer_horarios(mensaje)
            
            fecha_texto = None
            tipo_fecha = None
            fecha_dt = None
            
            horario_texto = None
            tipo_horario = None
            hora_tupla = None
            
            # Procesar fecha si existe
            if fechas:
                fechas_ordenadas = sorted(fechas, key=lambda f: mensaje.lower().find(f[0]))
                fecha_texto, tipo_fecha = fechas_ordenadas[-1]  # Tomar la última mencionada en el texto

                # Detectar cambio contextual
                if self.extractor.detectar_cambio_contextual(mensaje) and ultima_fecha_dt:
                    # Usar fecha anterior como referencia
                    fecha_dt = self.extractor.convertir_fecha_a_datetime(
                        fecha_texto, tipo_fecha, ultima_fecha_dt
                    )
                else:
                    fecha_dt = self.extractor.convertir_fecha_a_datetime(
                        fecha_texto, tipo_fecha
                    )
                
                ultima_fecha_completa = fecha_texto
                ultima_fecha_dt = fecha_dt
            
            # Procesar horario si existe
            if horarios:
                horario_texto, tipo_horario = horarios[-1]  # Tomar el último mencionado
                
                hora_tupla = self.extractor.convertir_horario_a_time(
                    horario_texto, tipo_horario, ultimo_horario_completo
                )
                
                # No actualizar si es "misma hora" o "duración"
                if tipo_horario not in ['misma_hora', 'duracion']:
                    ultimo_horario_completo = hora_tupla
            
            # Solo agregar evento si hay fecha o horario
            if fecha_dt or hora_tupla:
                # Si tenemos fecha y horario, combinarlos
                if fecha_dt and hora_tupla:
                    fecha_final = fecha_dt.replace(hour=hora_tupla[0], minute=hora_tupla[1])
                elif fecha_dt:
                    fecha_final = fecha_dt
                else:
                    # Solo horario sin fecha: usar hoy
                    ahora = self.extractor.ahora_mexico
                    fecha_final = ahora.replace(hour=hora_tupla[0], minute=hora_tupla[1], 
                                               second=0, microsecond=0)
                
                # Calcular fin (2 horas después por defecto)
                fecha_fin = fecha_final + timedelta(hours=2)
                
                evento = {
                    'mensaje': mensaje,
                    'indice': idx,
                    'fecha_texto': fecha_texto,
                    'horario_texto': horario_texto,
                    'fecha_inicio': fecha_final.isoformat(),
                    'fecha_fin': fecha_fin.isoformat(),
                    'fecha_inicio_legible': fecha_final.strftime('%d de %B de %Y a las %H:%M'),
                    'fecha_fin_legible': fecha_fin.strftime('%d de %B de %Y a las %H:%M'),
                }
                
                eventos.append(evento)
        
        # Preparar respuesta
        todas_fechas = list(set([e['fecha_texto'] for e in eventos if e['fecha_texto']]))
        todos_horarios = list(set([e['horario_texto'] for e in eventos if e['horario_texto']]))
        
        # Obtener el último evento para timeMin/timeMax principales
        time_min = None
        time_max = None
        if eventos:
            ultimo_evento = eventos[-1]
            time_min = ultimo_evento['fecha_inicio']
            time_max = ultimo_evento['fecha_fin']
        
        # Fecha y hora actual en México
        ahora_mx = self.extractor.ahora_mexico
        
        return {
            'eventos_detectados': eventos,
            'total_eventos': len(eventos),
            'fechas_mencionadas': todas_fechas,
            'horarios_mencionados': todos_horarios,
            'time_min': time_min,
            'time_max': time_max,
            'fecha_actual': ahora_mx.strftime('%d de %B de %Y'),
            'hora_actual': ahora_mx.strftime('%H:%M:%S'),
            'zona_horaria': 'America/Mexico_City',
            'fechas_procesadas': len(eventos) > 0,
        }