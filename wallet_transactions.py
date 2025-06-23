import configparser
import requests
from tabulate import tabulate
import sys
import os

def get_transactions(wallet_address):
    """
    Obtiene las transacciones de una direccion Bitcoin desde blockchain.info
    y las imprime en una tabla legible.
    """
    url = f"https://blockchain.info/rawaddr/{wallet_address}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Lanza excepcion si el codigo HTTP es error (4xx, 5xx)
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] No se pudo obtener datos desde la API: {e}")
        sys.exit(1)

    try:
        data = response.json()
    except ValueError:
        print("[ERROR] La respuesta no es un JSON valido.")
        sys.exit(1)

    transactions = data.get('txs', [])
    if not transactions:
        print("[INFO] No se encontraron transacciones para esta direccion.")
        return

    table = []
    for tx in transactions:
        tx_hash = tx.get('hash', 'N/A')
        inputs = [
            i['prev_out']['addr']
            for i in tx.get('inputs', [])
            if 'prev_out' in i and 'addr' in i['prev_out']
        ]
        from_addr = ', '.join(inputs) if inputs else 'N/A'

        for o in tx.get('out', []):
            to_addr = o.get('addr', 'N/A')
            value_btc = o.get('value', 0) / 1e8  # convertir de satoshis a BTC
            table.append([
                tx_hash[:10] + '...',  # Mostrar primeros 10 caracteres del hash
                from_addr,
                to_addr,
                value_btc
            ])

    # Mostrar los resultados en forma de tabla
    headers = ["Tx Hash", "From", "To", "Value (BTC)"]
    print(tabulate(table, headers=headers, tablefmt="grid"))

def load_wallet_from_config(config_path="config.ini"):
    """
    Lee la direccion de billetera (wallet) desde un archivo de configuracion.
    """
    if not os.path.exists(config_path):
        print(f"[ERROR] El archivo de configuracion '{config_path}' no existe.")
        sys.exit(1)

    config = configparser.ConfigParser()
    
    try:
        config.read(config_path)
        wallet = config['DEFAULT'].get('Target')
    except Exception as e:
        print(f"[ERROR] No se pudo leer el archivo de configuracion: {e}")
        sys.exit(1)

    if not wallet:
        print("[ERROR] El valor 'Target' no se encontro en el archivo de configuracion.")
        sys.exit(1)

    return wallet

# Programa principal
if __name__ == "__main__":
    wallet_address = load_wallet_from_config()
    get_transactions(wallet_address)
