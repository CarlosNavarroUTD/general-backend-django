import requests

BASE_URL = "http://localhost:8000/api"  # Ajusta según tu servidor
EMAIL = "carlos@eabmodel.com"
PASSWORD = "D3vp4ss"

def get_token():
    url = f"{BASE_URL}/token/"
    data = {"email": EMAIL, "password": PASSWORD}
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()["access"]
    else:
        raise Exception(f"Error al autenticar: {response.text}")

def create_flow(headers, name, description=""):
    url = f"{BASE_URL}/flows/"
    data = {"name": name, "description": description, "team": 1}  # Ajusta team si aplica
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def create_entity(headers, name, slug, type_="TEXT"):
    url = f"{BASE_URL}/entities/"
    data = {"name": name, "slug": slug, "type": type_, "team": 1}
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def create_node(headers, flow_id, title, message_template="", type_="QUESTION", collect_entity=None):
    url = f"{BASE_URL}/nodes/"
    data = {
        "flow": flow_id,
        "title": title,
        "message_template": message_template,
        "type": type_,
        "collect_entity": collect_entity
    }
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def create_path(headers, node_id, target_node_id, label="Siguiente"):
    url = f"{BASE_URL}/nodes/{node_id}/paths/"
    # ⚠️ Incluimos node_id explícitamente en el payload
    data = {"label": label, "node": node_id, "target_node": target_node_id}
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1️⃣ Crear flujo
    flow = create_flow(headers, name="Flujo Propiedades", description="Flujo para Patrimonium")
    flow_id = flow["id"]
    print("✅ Flujo creado:", flow)

    # 2️⃣ Crear entidad para proyecto de interés
    proyecto_entity = create_entity(headers, name="proyecto_interes", slug="proyecto_interes")
    proyecto_entity_id = proyecto_entity["id"]
    print("✅ Entidad creada:", proyecto_entity)

    # 3️⃣ Crear nodo inicial
    nodo_inicio = create_node(
        headers,
        flow_id,
        title="Bienvenida",
        message_template="¡Hola! Bienvenido a Patrimonium. ¿Está interesado en una propiedad o quiere conocer las opciones disponibles?",
        type_="QUESTION"
    )
    inicio_id = nodo_inicio["id"]
    print("✅ Nodo inicial creado:", nodo_inicio)

    # 4️⃣ Crear nodos de respuestas
    nodo_interes = create_node(
        headers,
        flow_id,
        title="Estoy interesado en una propiedad",
        message_template="Perfecto, por favor indíquenos la propiedad que le interesa",
        collect_entity=proyecto_entity_id
    )
    nodo_conocer = create_node(
        headers,
        flow_id,
        title="Quiero conocer las propiedades",
        message_template="Estas son las opciones disponibles: 1️⃣ Torres Real Vizcaya 2️⃣ Los Santos California 3️⃣ Torre Luna 4️⃣ Torre Alta Vista 5️⃣ Casas Bicentenario",
        type_="QUESTION"
    )
    print("✅ Nodos de respuesta creados")
    print(nodo_interes, nodo_conocer)

    # 5️⃣ Crear paths desde el nodo inicial
    path1 = create_path(headers, inicio_id, nodo_interes["id"], label="Estoy interesado")
    path2 = create_path(headers, inicio_id, nodo_conocer["id"], label="Quiero conocer")
    print("✅ Paths creados:", path1, path2)

if __name__ == "__main__":
    main()
