import requests

BASE_URL = "http://localhost:8000/api"   # Cambia si tu servidor está en otro host/puerto
EMAIL = "carlos@eabmodel.com"
PASSWORD = "D3vp4ss"

def get_token():
    url = f"{BASE_URL}/token/"
    data = {
        "email": EMAIL,
        "password": PASSWORD
    }
    try:
        response = requests.post(url, data=data)
    except requests.exceptions.RequestException as e:
        print("❌ Error de conexión:", e)
        return None

    if response.status_code == 200:
        token = response.json().get("access")
        if token:
            print("✅ Token obtenido:", token[:20], "...")
            return token
        else:
            print("⚠️ No se recibió un token válido:", response.json())
            return None
    else:
        print("❌ Error al autenticar:", response.status_code, response.text)
        return None


def get_flows(headers):
    url = f"{BASE_URL}/flows/"
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print("❌ Error al conectar con flujos:", e)
        return []

    print("\n📌 Flujos:")
    print(response.status_code, response.json())
    return response.json() if response.status_code == 200 else []


def get_nodes(headers, flow_id):
    url = f"{BASE_URL}/nodes/?flow={flow_id}"
    try:
        response = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con nodos del flujo {flow_id}:", e)
        return []

    print(f"\n📌 Nodos del flujo {flow_id}:")
    print(response.status_code, response.json())
    return response.json() if response.status_code == 200 else []


def main():
    token = get_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Obtener flujos
    flows = get_flows(headers)
    if flows and isinstance(flows, list) and len(flows) > 0:
        flow_id = flows[0].get("id")
        if flow_id:
            # Obtener nodos de ese flujo
            get_nodes(headers, flow_id)
        else:
            print("⚠️ El flujo no tiene ID válido.")
    else:
        print("⚠️ No hay flujos disponibles.")


if __name__ == "__main__":
    main()
