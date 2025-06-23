# BlockChainAnalyzer
Herramienta en Python que obtiene transacciones asociadas a una dirección de Bitcoin y dibuja un grafo que representa las relaciones entre direcciones emisoras y receptoras junto con los saldos netos.

# BC_Analyzer.py
# Visualiza y permite el análisis de transacciones Blockchain

Este proyecto analiza y visualiza transacciones en una blockchain almacenada en una base de datos SQLite. Construye un grafo dirigido de transacciones entre wallets y permite su exportación en formato **GraphML** o una visualización interactiva en **HTML** usando `vis.js`.

---

## Características

- Conexión automática a base de datos SQLite.
- Construcción de grafo dirigido (`networkx`) con nodos (wallets) y aristas (transacciones).
- Exportación a:
  - `GraphML` (para Gephi o análisis de redes).
  - `HTML interactivo` (visualización dinámica con vis.js).
- Visualización enriquecida:
  - Colores para roles de nodos (emisor, receptor, mixto).
  - Tabla de transacciones al seleccionar nodos/aristas.
  - Exportación de transacciones a CSV.

---

## Estructura de Archivos

├── BlockchainAnalyzer.py
├── config.ini
├── graph.graphml
├── transactions.html


---

##  Configuración 

`config.ini`
[DEFAULT]
Target = <wallet_address_or_transaction_hash>
Depth = 2

- `Target:` dirección de wallet (34 caracteres) o hash de transacción (64 caracteres).
- `Depth:` profundidad de análisis (0 = solo transacción inicial, mayor explora recursivamente).


Requisitos:
- Python 3.8+.
- SQLite3.
- networkx.
- vis.js (incluido vía CDN en HTML generado)
.
`python BC_Analyzer.py`
• Si la profundidad (Depth) es menor a 3, se genera también transactions.html con visualización interactiva, para mayor profundidad, se exporta solo graph.graphml.

## Estructura de Base de Datos Esperada
	• TRANSACT: contiene hash, time, input_total, output_total.
	• INPUTS: contiene transaction_hash, recipient, value, spending_transaction_hash.
	• OUTPUTS: contiene transaction_hash, recipient, value.

## Visualización HTML
	• Interactiva (zoom, click, tabla).
	• Leyenda de colores para nodos/aristas.
	• Exportación a CSV de transacciones por nodo.
	• Permite explorar flujos de BTC entre wallets.
![image](https://github.com/user-attachments/assets/4af5ef0f-48fb-4ca5-a8b4-d8d51a066173)

# wallet_transacciones.py

# Wallet Transaction Viewer
Este script consulta la API pública de [blockchain.info](https://blockchain.info) para recuperar y mostrar las transacciones de una dirección de Bitcoin especificada.
## 🚀 Características
- Obtiene transacciones de entrada y salida.
- Muestra una tabla formateada en consola.
- Lee la dirección desde un archivo `config.ini`.
## 📁 Estructura esperada de `config.ini`
```ini
[DEFAULT]
Target=1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

Requisitos
	• Python 3.7+
	• Paquetes:
		○ requests
		○ tabulate
Instalar dependencias con:
pip install requests tabulate

Ejecución
python wallet_transactions.py

Salida esperada

Una tabla como:
+---------------------+----------------------+----------------------+--------------+
| Tx Hash             | From                 | To                   | Value (BTC)  |
+---------------------+----------------------+----------------------+--------------+
| 4d5e6...            | 1AddressFrom         | 1AddressTo           | 0.054321     |
| ...                 | ...                  | ...                  | ...          |
+---------------------+----------------------+----------------------+--------------+



# wallet_transacciones_grafo.py
# Visualizador de transacciones Bitcoin
Este proyecto es una herramienta en Python que obtiene transacciones asociadas a una dirección de Bitcoin y dibuja un grafo que representa las relaciones entre direcciones emisoras y receptoras junto con los saldos netos.
---
## Características
- Lee la dirección destino desde un archivo de configuración (`config.ini`).
- Consulta la API pública de [blockchain.info](https://www.blockchain.info/) para obtener las transacciones.
- Calcula automáticamente los saldos netos por dirección.
- Genera un grafo dirigido con [`networkx`](https://networkx.org/) y [`matplotlib`](https://matplotlib.org/).
- Incluye manejo de errores robusto (timeout, claves faltantes, etc.).
---
## Requisitos
- Python 3.8 o superior
- Paquetes Python:
  - `requests`
  - `networkx`
  - `matplotlib`
  - `configparser`
Instálalos usando:
```bash
pip install requests networkx matplotlib

Archivo de configuración
Crea un archivo config.ini en la raíz del proyecto con el siguiente formato:
[DEFAULT]
Target = bc1qzktqgytzu8z6807tneqd8fre0z9lxfc0yaaf5enw7w0yjzsypclq6cjepy
Depth = 2
	Nota: Solo se usa el valor de Target. Depth está reservado para futuras funciones.

Uso
Ejecuta el programa desde la terminal:
python wallet_transacciones_grafo.py
Si la dirección existe y hay transacciones, verás un gráfico como este:
[INFO] Transacciones para bc1qzktqgytzu8z6807tneqd8fre0z9lxfc0yaaf5enw7w0yjzsypclq6cjepy

Cómo funciona
	1. load_wallet_from_config() carga la dirección desde config.ini.
	2. get_transactions() consulta la API blockchain.info y agrupa las transacciones.
	3. plot_transactions() crea un grafo donde:
		○ Los nodos rojos son emisores.
		○ Los nodos verdes son receptores.
		○ Las aristas muestran la cantidad transferida.
		○ Cada nodo también muestra su saldo neto en BTC.

Errores comunes
	• Archivo config.ini faltante: crea el archivo antes de ejecutar.
	• Falta la clave Target: asegúrate que el parámetro Target esté en la sección [DEFAULT].
	• API no disponible: verifica tu conexión a internet.

Estructura del proyecto
project/
├─ config.ini
├─ main.py
├─ README.md
├─ requirements.txt






