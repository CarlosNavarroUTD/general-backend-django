# apps/citas/utils/date_time_extractor.py
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pytz

class DateTimeExtractor:
    """
    Extractor mejorado de fechas y horarios del texto en español.
    Maneja contextos conversacionales y zona horaria de México.
    """
    
    TIMEZONE = pytz.timezone('America/Mexico_City')
    
    MESES = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    DIAS_SEMANA = {
        'lunes': 0, 'martes': 1, 'miércoles': 2, 'miercoles': 2,
        'jueves': 3, 'viernes': 4, 'sábado': 5, 'sabado': 5, 'domingo': 6
    }
    
    # Palabras que indican cambio contextual
    PALABRAS_CAMBIO = [
        'entonces', 'después', 'luego', 'pero', 'mejor', 
        'cambiemos', 'cambio', 'más bien', 'en realidad'
    ]
    
    # Modificadores de tiempo
    MODIFICADORES_SEMANA = ['siguiente', 'próxima', 'proxima', 'que viene', 'entrante']
    MODIFICADORES_MES = ['siguiente', 'próximo', 'proximo', 'que viene', 'entrante']
    
    def __init__(self):
        self.ahora_mexico = datetime.now(self.TIMEZONE)
    
    def extraer_fechas(self, texto: str) -> List[Tuple[str, str]]:
        """
        Extrae todas las fechas mencionadas en el texto.
        Retorna lista de tuplas (texto_encontrado, tipo_patron)
        """
        fechas = []
        texto_lower = texto.lower()
        
        # Patrón: "30 de junio de 2025", "20 de mayo"
        patron = r'(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+(?:de|del)\s+(\d{4}))?'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'dia_mes_año'))
        
        # Patrón: "junio 30", "mayo 20"
        patron = r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(\d{1,2})'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'mes_dia'))
        
        # Patrón: "30/06/2025", "20-05-2025"
        patron = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'
        for match in re.finditer(patron, texto):
            fechas.append((match.group(0), 'dia_mes_año_slash'))
        
        # Patrón: "30/06", "20-05"
        patron = r'(\d{1,2})[\/\-](\d{1,2})(?![\/\-\d])'
        for match in re.finditer(patron, texto):
            fechas.append((match.group(0), 'dia_mes_slash'))
        
        # Patrón: "lunes 23", "martes 15"
        patron = r'(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+(\d{1,2})'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'diasemana_numero'))
        
        # Patrón: "el lunes 23"
        patron = r'el\s+(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+(\d{1,2})'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'el_diasemana_numero'))
        
        # Patrón: "este lunes", "próximo martes"
        patron = r'(este|esta|próximo|proximo|próxima|proxima|siguiente)\s+(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'modificador_diasemana'))
        
        # Patrón: "mañana", "pasado mañana"
        patron = r'(mañana|pasado\s+mañana)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'relativo'))
        
        # Patrón: "hoy", "today"
        patron = r'\b(hoy|today)\b'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'hoy'))
        
        # Patrón: "la siguiente semana", "la próxima semana", "semana que viene"
        patron = r'(?:la\s+)?(siguiente|próxima|proxima)\s+semana|semana\s+(?:que\s+viene|entrante)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'semana_siguiente'))
        
        # Patrón: "esta semana"
        patron = r'esta\s+semana'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'esta_semana'))
        
        # Patrón: "el próximo mes", "mes que viene", "mes entrante"
        patron = r'(?:el\s+)?(siguiente|próximo|proximo)\s+mes|mes\s+(?:que\s+viene|entrante)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'mes_siguiente'))
        
        # Patrón: "este mes"
        patron = r'este\s+mes'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'este_mes'))
        
        # Patrón: "fin de semana", "este fin de semana", "próximo fin de semana"
        patron = r'(?:(este|próximo|proximo|siguiente)\s+)?fin\s+de\s+semana'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'fin_de_semana'))
        
        # Patrón: "el día 15", "día 23"
        patron = r'(?:el\s+)?día\s+(\d{1,2})'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'dia_numero'))
        
        # Patrón: "dentro de 3 días", "en 5 días"
        patron = r'(?:dentro\s+de|en)\s+(\d+)\s+días?'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'dias_futuro'))
        
        # Patrón: "dentro de 2 semanas", "en 3 semanas"
        patron = r'(?:dentro\s+de|en)\s+(\d+)\s+semanas?'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'semanas_futuro'))
        
        # Patrón: "dentro de 2 meses", "en 3 meses"
        patron = r'(?:dentro\s+de|en)\s+(\d+)\s+meses?'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            fechas.append((match.group(0), 'meses_futuro'))
        
        # Patrón: Solo días de la semana "lunes", "el martes"
        patron = r'\b(?:el\s+)?(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\b'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            # Evitar duplicados si ya fue capturado con número
            texto_match = match.group(0)
            if not any(texto_match in f[0] for f in fechas):
                fechas.append((texto_match, 'solo_diasemana'))
        
        return fechas
    
    def extraer_horarios(self, texto: str) -> List[Tuple[str, str]]:
        """
        Extrae todos los horarios mencionados en el texto.
        Retorna lista de tuplas (texto_encontrado, tipo_patron)
        """
        horarios = []
        texto_lower = texto.lower()
        
        # Filtros para evitar falsos positivos
        if self._es_numero_personas(texto_lower):
            return horarios
        if self._es_año_solo(texto):
            return horarios
        if self._es_medida(texto_lower):
            return horarios
        if self._es_telefono(texto):
            return horarios
        
        # Patrón: "10:30 pm", "14:30", "2:15 am"
        patron = r'(\d{1,2}):(\d{2})\s*(pm|am)?'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'hora_minutos'))
        
        # Patrón: "10 pm", "2 am" (evitar años)
        patron = r'(?<!\d)(\d{1,2})\s+(pm|am)(?!\d)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'hora_ampm'))
        
        # Patrón: "de 10 a 11", "desde las 10 hasta las 11"
        patron = r'(?:de|desde)\s+(?:las?\s+)?(\d{1,2})(?::(\d{2}))?\s*(?:pm|am)?\s+(?:a|hasta)\s+(?:las?\s+)?(\d{1,2})(?::(\d{2}))?\s*(pm|am)?'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'rango'))
        
        # Patrón: "a las 3", "a las 10:30"
        patron = r'a\s+las?\s+(\d{1,2})(?::(\d{2}))?(?!\d)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'a_las'))
        
        # Patrón: "las 3", "las 10:30" (evitar "de las")
        patron = r'(?<!de\s)las\s+(\d{1,2})(?::(\d{2}))?(?!\d)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            if not any(match.group(0) in h[0] for h in horarios):
                horarios.append((match.group(0), 'las'))
        
        # Patrón: "por la mañana/tarde/noche"
        patron = r'(por\s+la\s+mañana|por\s+la\s+tarde|por\s+la\s+noche|en\s+la\s+mañana|en\s+la\s+tarde|en\s+la\s+noche)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'periodo_dia'))
        
        # Patrón: "al mediodía", "a medianoche"
        patron = r'(al\s+mediodía|al\s+mediodia|a\s+medianoche|mediodía|mediodia|medianoche)'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'momento_especial'))
        
        # Patrón: "misma hora", "a la misma hora"
        patron = r'(a\s+la\s+)?misma\s+hora'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'misma_hora'))
        
        # Patrón: "temprano", "muy temprano"
        patron = r'(muy\s+)?temprano'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'temprano'))
        
        # Patrón: "tarde", "más tarde"
        patron = r'(más|mas)\s+tarde\b'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'mas_tarde'))
        
        # Patrón: "3 horas" (duración, no horario)
        patron = r'(\d+)\s+(horas?|hrs?|h)\b'
        for match in re.finditer(patron, texto_lower, re.IGNORECASE):
            horarios.append((match.group(0), 'duracion'))
        
        return horarios
    
    def _es_numero_personas(self, texto: str) -> bool:
        """Detecta si el texto habla de cantidad de personas"""
        return bool(re.search(r'\d+\s*(personas?|gente|asistentes?|invitados?|pax)', texto, re.IGNORECASE))
    
    def _es_año_solo(self, texto: str) -> bool:
        """Detecta si hay años mencionados (1900-2099)"""
        return bool(re.search(r'\b(19|20)\d{2}\b', texto)) and not bool(re.search(r'\b(19|20)\d{2}:\d{2}\b', texto))
    
    def _es_medida(self, texto: str) -> bool:
        """Detecta si el texto habla de medidas"""
        return bool(re.search(r'\d+\s*(metros?|km|centímetros?|litros?|kilos?|gramos?)', texto, re.IGNORECASE))
    
    def _es_telefono(self, texto: str) -> bool:
        """Detecta si hay números de teléfono"""
        return bool(re.search(r'\d{3,4}[-\s]?\d{3,4}[-\s]?\d{3,4}', texto))
    
    def convertir_fecha_a_datetime(self, fecha_texto: str, tipo_patron: str, 
                                   fecha_anterior: Optional[datetime] = None) -> datetime:
        """
        Convierte texto de fecha a objeto datetime.
        Considera contexto de fecha anterior si existe.
        """
        fecha_texto_lower = fecha_texto.lower()
        ahora = self.ahora_mexico
        
        # Mañana
        if tipo_patron == 'relativo' and 'mañana' in fecha_texto_lower:
            if 'pasado' in fecha_texto_lower:
                return ahora + timedelta(days=2)
            return ahora + timedelta(days=1)
        
        # Hoy
        if tipo_patron == 'hoy':
            return ahora
        
        # "la siguiente semana", "semana que viene"
        if tipo_patron == 'semana_siguiente':
            # Sumar 7 días (mismo día de la semana, siguiente semana)
            return (ahora + timedelta(days=7)).replace(hour=14, minute=0, second=0, microsecond=0)

        # "esta semana"
        if tipo_patron == 'esta_semana':
            # Ir al lunes de esta semana
            dias_desde_lunes = ahora.weekday()
            return (ahora - timedelta(days=dias_desde_lunes)).replace(hour=14, minute=0, second=0, microsecond=0)
        
        # "el próximo mes", "mes que viene"
        if tipo_patron == 'mes_siguiente':
            if ahora.month == 12:
                return ahora.replace(year=ahora.year + 1, month=1, day=1, hour=14, minute=0, second=0, microsecond=0)
            else:
                return ahora.replace(month=ahora.month + 1, day=1, hour=14, minute=0, second=0, microsecond=0)
        
        # "este mes"
        if tipo_patron == 'este_mes':
            return ahora.replace(day=1, hour=14, minute=0, second=0, microsecond=0)
        
        # "fin de semana"
        if tipo_patron == 'fin_de_semana':
            modificador = None
            match = re.search(r'(este|próximo|proximo|siguiente)', fecha_texto_lower)
            if match:
                modificador = match.group(1)
            
            # Encontrar el siguiente sábado
            dias_hasta_sabado = (5 - ahora.weekday()) % 7
            if dias_hasta_sabado == 0 and ahora.hour >= 12:
                dias_hasta_sabado = 7  # Si es sábado tarde, ir al siguiente
            
            if modificador in ['próximo', 'proximo', 'siguiente']:
                dias_hasta_sabado += 7
            
            return (ahora + timedelta(days=dias_hasta_sabado)).replace(hour=14, minute=0, second=0, microsecond=0)
        
        # "dentro de X días" o "en X días"
        if tipo_patron == 'dias_futuro':
            match = re.search(r'(\d+)', fecha_texto)
            if match:
                dias = int(match.group(1))
                return ahora + timedelta(days=dias)
        
        # "dentro de X semanas" o "en X semanas"
        if tipo_patron == 'semanas_futuro':
            match = re.search(r'(\d+)', fecha_texto)
            if match:
                semanas = int(match.group(1))
                return ahora + timedelta(weeks=semanas)
        
        # "dentro de X meses" o "en X meses"
        if tipo_patron == 'meses_futuro':
            match = re.search(r'(\d+)', fecha_texto)
            if match:
                meses = int(match.group(1))
                mes_futuro = ahora.month + meses
                año_futuro = ahora.year
                while mes_futuro > 12:
                    mes_futuro -= 12
                    año_futuro += 1
                return ahora.replace(year=año_futuro, month=mes_futuro, hour=14, minute=0, second=0, microsecond=0)
        
        # "30 de junio de 2025" o "20 de mayo"
        if tipo_patron == 'dia_mes_año':
            match = re.search(r'(\d{1,2})\s+de\s+(\w+)(?:\s+(?:de|del)\s+(\d{4}))?', fecha_texto_lower)
            if match:
                dia = int(match.group(1))
                mes = self.MESES.get(match.group(2))
                año = int(match.group(3)) if match.group(3) else ahora.year
                
                # Si el mes/día ya pasó este año, usar el siguiente
                fecha_candidata = ahora.replace(year=año, month=mes, day=dia, hour=14, minute=0, second=0, microsecond=0)
                if fecha_candidata < ahora and not match.group(3):
                    fecha_candidata = fecha_candidata.replace(year=año + 1)
                
                return fecha_candidata
        
        # "junio 30"
        if tipo_patron == 'mes_dia':
            match = re.search(r'(\w+)\s+(\d{1,2})', fecha_texto_lower)
            if match:
                mes = self.MESES.get(match.group(1))
                dia = int(match.group(2))
                año = ahora.year
                
                fecha_candidata = ahora.replace(year=año, month=mes, day=dia, hour=14, minute=0, second=0, microsecond=0)
                if fecha_candidata < ahora:
                    fecha_candidata = fecha_candidata.replace(year=año + 1)
                
                return fecha_candidata
        
        # "30/06/2025" o "30-06-2025"
        if tipo_patron == 'dia_mes_año_slash':
            match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', fecha_texto)
            if match:
                dia = int(match.group(1))
                mes = int(match.group(2))
                año = int(match.group(3))
                return ahora.replace(year=año, month=mes, day=dia, hour=14, minute=0, second=0, microsecond=0)
        
        # "30/06" o "20-05"
        if tipo_patron == 'dia_mes_slash':
            match = re.search(r'(\d{1,2})[\/\-](\d{1,2})', fecha_texto)
            if match:
                dia = int(match.group(1))
                mes = int(match.group(2))
                año = ahora.year
                
                fecha_candidata = ahora.replace(year=año, month=mes, day=dia, hour=14, minute=0, second=0, microsecond=0)
                if fecha_candidata < ahora:
                    fecha_candidata = fecha_candidata.replace(year=año + 1)
                
                return fecha_candidata
        
        # "lunes 23", "el martes 15"
        if tipo_patron in ['diasemana_numero', 'el_diasemana_numero']:
            match = re.search(r'(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)\s+(\d{1,2})', fecha_texto_lower)
            if match:
                dia_semana_nombre = match.group(1)
                dia_numero = int(match.group(2))
                dia_semana_obj = self.DIAS_SEMANA.get(dia_semana_nombre)
                
                # Buscar la próxima fecha que coincida
                for i in range(60):  # Buscar en los próximos 60 días
                    fecha_prueba = ahora + timedelta(days=i)
                    if fecha_prueba.weekday() == dia_semana_obj and fecha_prueba.day == dia_numero:
                        return fecha_prueba.replace(hour=14, minute=0, second=0, microsecond=0)
                
                # Fallback: asumir mes actual o siguiente
                mes = ahora.month
                año = ahora.year
                try:
                    fecha_candidata = ahora.replace(year=año, month=mes, day=dia_numero, hour=14, minute=0, second=0, microsecond=0)
                    if fecha_candidata < ahora:
                        if mes == 12:
                            fecha_candidata = ahora.replace(year=año + 1, month=1, day=dia_numero, hour=14, minute=0, second=0, microsecond=0)
                        else:
                            fecha_candidata = ahora.replace(month=mes + 1, day=dia_numero, hour=14, minute=0, second=0, microsecond=0)
                    return fecha_candidata
                except ValueError:
                    # Día inválido para el mes
                    pass
        
        # "este lunes", "próximo martes"
        if tipo_patron == 'modificador_diasemana':
            match = re.search(r'(este|esta|próximo|proximo|próxima|proxima|siguiente)\s+(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)', fecha_texto_lower)
            if match:
                modificador = match.group(1)
                dia_semana_nombre = match.group(2)
                dia_semana_obj = self.DIAS_SEMANA.get(dia_semana_nombre)
                
                dias_hasta = (dia_semana_obj - ahora.weekday() + 7) % 7
                if dias_hasta == 0:
                    dias_hasta = 7  # Siguiente semana
                if modificador in ['próximo', 'proximo', 'próxima', 'proxima', 'siguiente']:
                    dias_hasta += 7
                
                return (ahora + timedelta(days=dias_hasta)).replace(hour=14, minute=0, second=0, microsecond=0)
        
        # "el día 15", "día 23"
        if tipo_patron == 'dia_numero':
            match = re.search(r'(\d{1,2})', fecha_texto)
            if match:
                dia = int(match.group(1))
                mes = ahora.month
                año = ahora.year
                
                try:
                    fecha_candidata = ahora.replace(year=año, month=mes, day=dia, hour=14, minute=0, second=0, microsecond=0)
                    if fecha_candidata < ahora:
                        if mes == 12:
                            fecha_candidata = ahora.replace(year=año + 1, month=1, day=dia, hour=14, minute=0, second=0, microsecond=0)
                        else:
                            fecha_candidata = ahora.replace(month=mes + 1, day=dia, hour=14, minute=0, second=0, microsecond=0)
                    return fecha_candidata
                except ValueError:
                    pass
        
        # Solo día de la semana "lunes", "el martes"
        if tipo_patron == 'solo_diasemana':
            match = re.search(r'(lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo)', fecha_texto_lower)
            if match:
                dia_semana_nombre = match.group(1)
                dia_semana_obj = self.DIAS_SEMANA.get(dia_semana_nombre)
                
                dias_hasta = (dia_semana_obj - ahora.weekday() + 7) % 7
                if dias_hasta == 0:
                    dias_hasta = 7
                
                return (ahora + timedelta(days=dias_hasta)).replace(hour=14, minute=0, second=0, microsecond=0)
        
        # Default: hoy a las 2 PM
        return ahora.replace(hour=14, minute=0, second=0, microsecond=0)
    
    def convertir_horario_a_time(self, horario_texto: str, tipo_patron: str,
                                 horario_anterior: Optional[Tuple[int, int]] = None) -> Tuple[int, int]:
        """
        Convierte texto de horario a tupla (hora, minutos).
        Considera horario anterior si el texto hace referencia a él.
        """
        horario_texto_lower = horario_texto.lower()
        
        # "misma hora"
        if tipo_patron == 'misma_hora' and horario_anterior:
            return horario_anterior
        
        # "duración" - no es horario específico
        if tipo_patron == 'duracion':
            return (14, 0)  # Default
        
        # "temprano" -> 8:00 AM
        if tipo_patron == 'temprano':
            if 'muy' in horario_texto_lower:
                return (7, 0)
            return (8, 0)
        
        # "más tarde" -> 4:00 PM
        if tipo_patron == 'mas_tarde':
            return (16, 0)
        
        # "10:30 pm", "14:30", "2:15 am"
        if tipo_patron == 'hora_minutos':
            match = re.search(r'(\d{1,2}):(\d{2})\s*(pm|am)?', horario_texto_lower)
            if match:
                hora = int(match.group(1))
                minutos = int(match.group(2))
                periodo = match.group(3)
                
                if periodo:
                    if periodo == 'pm' and hora != 12:
                        hora += 12
                    elif periodo == 'am' and hora == 12:
                        hora = 0
                
                return (hora, minutos)
        
        # "10 pm", "2 am"
        if tipo_patron == 'hora_ampm':
            match = re.search(r'(\d{1,2})\s+(pm|am)', horario_texto_lower)
            if match:
                hora = int(match.group(1))
                periodo = match.group(2)
                
                if periodo == 'pm' and hora != 12:
                    hora += 12
                elif periodo == 'am' and hora == 12:
                    hora = 0
                
                return (hora, 0)
        
        # "a las 3", "las 10"
        if tipo_patron in ['a_las', 'las']:
            match = re.search(r'(\d{1,2})(?::(\d{2}))?', horario_texto)
            if match:
                hora = int(match.group(1))
                minutos = int(match.group(2)) if match.group(2) else 0
                
                # Asumir PM para horas 1-7, AM/24h para el resto
                if 1 <= hora <= 7:
                    hora += 12
                
                return (hora, minutos)
        
        # "por la mañana" -> 9:00
        if tipo_patron == 'periodo_dia':
            if 'mañana' in horario_texto_lower:
                return (9, 0)
            elif 'tarde' in horario_texto_lower:
                return (15, 0)
            elif 'noche' in horario_texto_lower:
                return (20, 0)
        
        # "mediodía" -> 12:00, "medianoche" -> 00:00
        if tipo_patron == 'momento_especial':
            if 'mediodia' in horario_texto_lower or 'mediodía' in horario_texto_lower:
                return (12, 0)
            elif 'medianoche' in horario_texto_lower:
                return (0, 0)
        
        # Rango: tomar la hora de inicio
        if tipo_patron == 'rango':
            match = re.search(r'(\d{1,2})(?::(\d{2}))?', horario_texto)
            if match:
                hora = int(match.group(1))
                minutos = int(match.group(2)) if match.group(2) else 0
                return (hora, minutos)
        
        # Default: 2 PM
        return (14, 0)
    
    def detectar_cambio_contextual(self, mensaje: str) -> bool:
        """Detecta si el mensaje indica un cambio contextual"""
        mensaje_lower = mensaje.lower()
        return any(palabra in mensaje_lower for palabra in self.PALABRAS_CAMBIO)