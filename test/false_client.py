import requests

BASE_URL = "http://localhost:8000/api"
EMAIL = "carlos@eabmodel.com"
PASSWORD = "D3vp4ss"
SENDER_ID = "user_123"

def get_token():
    r = requests.post(f"{BASE_URL}/token/", data={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access"]

def get_flows(headers):
    r = requests.get(f"{BASE_URL}/flows/", headers=headers)
    r.raise_for_status()
    return r.json()

def get_nodes(headers, flow_id):
    r = requests.get(f"{BASE_URL}/nodes/?flow={flow_id}", headers=headers)
    r.raise_for_status()
    return r.json()

def get_paths(headers, node_id):
    r = requests.get(f"{BASE_URL}/nodes/{node_id}/paths/", headers=headers)
    r.raise_for_status()
    return r.json()

def save_entity_value(headers, entity_id, team_id, sender_id, value):
    data = {"entity": entity_id, "team": team_id, "sender_id": sender_id, "value": value}
    r = requests.post(f"{BASE_URL}/entity_values/", json=data, headers=headers)
    r.raise_for_status()
    return r.json()

def run_flow():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    flows = get_flows(headers)
    if not flows:
        print("No hay flujos disponibles")
        return

    flow = flows[0]
    flow_id = flow["id"]
    nodes = get_nodes(headers, flow_id)

    node_dict = {n["id"]: n for n in nodes}

    # Comenzamos con el primer nodo (suponemos que es el primero en la lista)
    current_node = nodes[0]

    while current_node:
        print(f"\n💬 {current_node['message_template']}")
        
        # Si recolecta entidad
        collect_entity = current_node.get("collect_entity")
        if collect_entity:
            value = input("🔹 Su respuesta: ")
            save_entity_value(headers, collect_entity, flow["team"], SENDER_ID, value)

        # Revisar paths
        paths = get_paths(headers, current_node["id"])
        if not paths:
            print("✅ Fin del flujo.")
            break

        if len(paths) == 1:
            next_node_id = paths[0]["target_node"]
        else:
            # Mostrar opciones de paths
            print("Opciones de continuación:")
            for i, p in enumerate(paths):
                print(f"{i+1}. {p['label']}")
            choice = input("Seleccione opción: ")
            try:
                choice_idx = int(choice) - 1
                next_node_id = paths[choice_idx]["target_node"]
            except:
                print("Opción inválida, terminando flujo.")
                break

        if not next_node_id:
            print("✅ Fin del flujo.")
            break

        current_node = node_dict.get(next_node_id)

if __name__ == "__main__":
    run_flow()
