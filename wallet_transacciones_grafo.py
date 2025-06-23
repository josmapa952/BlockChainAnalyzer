import configparser
import requests
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
import os
import sys

def load_wallet_from_config(config_path="config.ini"):
    """
    Lee la direccion de la wallet desde un archivo de configuracion config.ini.

    Parametros:
        config_path (str): Ruta al archivo de configuracion.

    Retorna:
        str: La direccion de la wallet leida.
    """
    # Validar que el archivo exista
    if not os.path.exists(config_path):
        print(f"[ERROR] Archivo de configuracion '{config_path}' no encontrado.")
        sys.exit(1)

    config = configparser.ConfigParser()

    try:
        config.read(config_path)  # Cargar config
        wallet_address = config['DEFAULT'].get('Target')
        if not wallet_address:
            raise ValueError("La clave 'Target' esta vacia o ausente en config.ini")
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo de configuracion: {e}")
        sys.exit(1)

    return wallet_address


def get_transactions(wallet_address):
    """
    Obtiene las transacciones asociadas a una direccion Bitcoin desde blockchain.info.

    Parametros:
        wallet_address (str): La direccion Bitcoin.

    Retorna:
        tuple: Un diccionario de transacciones y un diccionario de saldos.
    """
    url = f"https://blockchain.info/rawaddr/{wallet_address}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Genera error para status != 200
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error en la solicitud HTTP a blockchain.info: {e}")
        return {}, {}

    # Intentar decodificar la respuesta JSON
    try:
        data = response.json()
    except ValueError:
        print("[ERROR] La respuesta no es un JSON valido.")
        return {}, {}

    transactions = data.get('txs', [])
    grouped_transactions = {}
    balances = {}

    # Procesar cada transaccion
    for tx in transactions:
        timestamp = tx.get('time', 0)
        date = datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        inputs = [i['prev_out']['addr'] for i in tx.get('inputs', []) if i.get('prev_out', {}).get('addr')]
        outputs = [o['addr'] for o in tx.get('out', []) if o.get('addr')]

        amount_satoshis = sum(o.get('value', 0) for o in tx.get('out', []))
        amount_btc = amount_satoshis / 1e8

        # Actualizar saldo por direcciones
        for sender in inputs:
            balances[sender] = balances.get(sender, 0) - amount_btc
        for receiver in outputs:
            balances[receiver] = balances.get(receiver, 0) + amount_btc

        grouped_transactions[tx.get('hash', 'Unknown')] = {
            'date': date,
            'from': inputs,
            'to': outputs,
            'amount_btc': amount_btc
        }

    return grouped_transactions, balances


def plot_transactions(transactions, balances, wallet_address):
    """
    Dibuja un grafo dirigido con las transacciones entre direcciones.

    Parametros:
        transactions (dict): Diccionario con detalles de transacciones.
        balances (dict): Saldos calculados para cada direccion.
        wallet_address (str): La direccion objetivo para el titulo.
    """
    G = nx.DiGraph()     # Grafo dirigido
    node_colors = {}

    # Construir nodos y aristas
    for tx_hash, details in transactions.items():
        for sender in details['from']:
            for receiver in details['to']:
                G.add_edge(sender, receiver, label=f"{details['amount_btc']} BTC")
                node_colors[sender] = 'red'
                node_colors[receiver] = 'green'

    node_list = list(G.nodes())
    color_map = [node_colors.get(node, 'blue') for node in node_list]

    # Calcular layout del grafo
    pos = nx.spring_layout(G, seed=42)

    # Dibujar grafo sin etiquetas
    plt.figure(figsize=(14, 8))
    nx.draw(
        G, pos, with_labels=False,
        node_color=color_map, edge_color='gray',
        node_size=1500, font_size=8, font_weight="bold"
    )

    # Etiquetas con saldo en cada nodo
    labels_with_balance = {
        node: f"{node}\n{balances.get(node, 0):.5f} BTC"
        for node in G.nodes()
    }
    nx.draw_networkx_labels(G, pos, labels=labels_with_balance, font_size=7)

    # Etiquetas para los montos en las aristas
    edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7)

    # Titulo del grafico
    plt.title(f"Transacciones de {wallet_address} con Saldos")
    plt.axis('off')
    plt.show()


# ==================== Programa principal ====================
if __name__ == "__main__":
    # Cargar wallet desde config.ini
    wallet_address = load_wallet_from_config()

    # Obtener transacciones
    transactions, balances = get_transactions(wallet_address)

    # Graficar solo si hay transacciones
    if transactions:
        plot_transactions(transactions, balances, wallet_address)
    else:
        print("[INFO] No hay transacciones para esta direccion o hubo un error en la consulta.")
