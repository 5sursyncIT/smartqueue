# apps/locations/utils.py
"""
Utilitaires pour les calculs géographiques SmartQueue
"""

import math

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculer distance entre deux points GPS avec formule Haversine
    
    Args:
        lat1, lon1: Latitude/longitude point 1
        lat2, lon2: Latitude/longitude point 2
    
    Returns:
        Distance en kilomètres
    """
    # Convertir degrés en radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Formule Haversine
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Rayon de la Terre en km
    r = 6371
    
    return round(c * r, 2)