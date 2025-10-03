# integraciones/services/google_maps.py

import requests
from django.conf import settings

def obtener_comentarios_google(place_id, access_token):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "review"
    }
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, params=params, headers=headers)
    return response.json()


