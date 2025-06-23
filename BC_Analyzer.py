import sqlite3
import configparser
import networkx as nx
from datetime import datetime
from typing import Dict, Set


class BlockchainAnalyzer:
    """
    Clase principal para analizar y visualizar transacciones en una blockchain
    almacenada en una base de datos SQLite. Construye un grafo dirigido donde los nodos
    son wallets y los arcos representan transacciones.
    """
    def __init__(self, db_path: str = 'BC.db'):
        """
        Inicializa la conexion con la base de datos y estructuras de datos.
        """
        try:
            self.conn = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            raise RuntimeError(f"Error al conectar a la base de datos: {e}")
        self.G = nx.DiGraph()
        self.wallet_balances: Dict[str, float] = {}
        self.visited_transactions: Set[str] = set()
        
    def save_graphml(self, filename: str = "graph.graphml"):
        """
        Exporta el grafo en formato GraphML, util para analisis en herramientas como Gephi.
        """
        try:
            nx.write_graphml(self.G, filename)
            print(f"Grafo exportado exitosamente en formato GraphML a {filename}")
        except Exception as e:
            print(f"Error al exportar GraphML: {e}")
            

    def _update_wallet_balance(self, wallet: str, amount: float):
        """
        Actualiza el balance de un wallet sumando el monto dado.
        """
        self.wallet_balances[wallet] = self.wallet_balances.get(wallet, 0.0) + amount

    def _process_transaction(self, tx_hash: str, current_depth: int, max_depth: int):
        """
        Procesa una transaccion especifica, actualiza el grafo con sus relaciones,
        y explora recursivamente transacciones relacionadas hasta el nivel deseado.
        """
        if tx_hash in self.visited_transactions:
            return
        self.visited_transactions.add(tx_hash)

        try:
            tx_data = self.conn.execute('''
                SELECT hash, time, input_total, output_total 
                FROM TRANSACT WHERE hash = ?
            ''', (tx_hash,)).fetchone()
        except sqlite3.Error as e:
            print(f"Error al consultar transaccion {tx_hash}: {e}")
            return

        if not tx_data:
            return

        tx_hash, tx_time, input_total, output_total = tx_data
        try:
            tx_datetime = datetime.strptime(tx_time, '%Y-%m-%d %H:%M:%S')
        except Exception:
            try:
                tx_datetime = datetime.fromtimestamp(int(tx_time))
            except Exception:
                print(f"Formato de fecha invalido para transaccion {tx_hash}")
                return
        tx_date = tx_datetime.strftime('%Y-%m-%d')

        try:
            inputs = self.conn.execute('''
                SELECT recipient, value 
                FROM INPUTS 
                WHERE transaction_hash = ?
            ''', (tx_hash,)).fetchall()

            outputs = self.conn.execute('''
                SELECT recipient, value 
                FROM OUTPUTS 
                WHERE transaction_hash = ?
            ''', (tx_hash,)).fetchall()
        except sqlite3.Error as e:
            print(f"Error al obtener inputs/outputs de {tx_hash}: {e}")
            return

        for sender, input_value in inputs:
            for receiver, output_value in outputs:
                self.G.add_edge(
                    sender,
                    receiver,
                    tx_id=tx_hash,
                    value=output_value,
                    date=tx_date
                )
                self._update_wallet_balance(sender, -float(input_value))
                self._update_wallet_balance(receiver, float(output_value))

        if max_depth == 0 or current_depth < max_depth:
            next_depth = current_depth + 1
            for output in outputs:
                try:
                    next_txs = self.conn.execute('''
                        SELECT spending_transaction_hash 
                        FROM INPUTS 
                        WHERE recipient = ? AND spending_transaction_hash IS NOT NULL
                    ''', (output[0],)).fetchall()
                except sqlite3.Error as e:
                    print(f"Error al buscar siguientes transacciones: {e}")
                    continue

                for (next_tx,) in next_txs:
                    self._process_transaction(next_tx, next_depth, max_depth)

    def build_graph(self, target: str, max_depth: int = 0):
        """
        Construye el grafo a partir de una direccion (wallet) o un hash de transaccion.
        Determina automaticamente que tipo es por la longitud del string.
        """
        if len(target) == 64:
            self._process_transaction(target, 1, max_depth)
        else:
            try:
                txs = self.conn.execute('''
                    SELECT transaction_hash FROM INPUTS WHERE recipient = ?
                    UNION
                    SELECT transaction_hash FROM OUTPUTS WHERE recipient = ?
                ''', (target, target)).fetchall()
            except sqlite3.Error as e:
                print(f"Error al obtener transacciones del wallet {target}: {e}")
                return

            for (tx_hash,) in txs:
                self._process_transaction(tx_hash, 1, max_depth)

        # Asigna atributos de balance a cada nodo
        for node in self.G.nodes():
            balance = self.wallet_balances.get(node, 0.0)
            self.G.nodes[node]['balance'] = balance
            self.G.nodes[node]['label'] = f"{node[:6]}...{node[-4:]}\nBalance: {balance:.8f} BTC"

    def save_html_graph(self, filename: str = "transactions.html"):
        """
        Genera una visualizacion HTML interactiva del grafo utilizando vis.js.
        Muestra una tabla con transacciones al hacer clic en cada nodo.
        """
        try:
            import json
        except ImportError:
            raise ImportError("Falta el modulo 'json', requerido para guardar el grafo en HTML")


        node_roles = {}
        for u, v in self.G.edges():
            node_roles.setdefault(u, set()).add("sender")
            node_roles.setdefault(v, set()).add("receiver")

        nodes = []
        for node, data in self.G.nodes(data=True):
            roles = node_roles.get(node, set())
            if roles == {"sender"}:
                color = "#FF6B6B"
            elif roles == {"receiver"}:
                color = "#66BB6A"
            else:
                color = "#FFA726"
            nodes.append({
                "id": node,
                "label": f"{node[:6]}...{node[-4:]}",
                "originalLabel": f"{node[:6]}...{node[-4:]}", 
                "title": f"Balance: {data.get('balance', 0.0):.8f} BTC",
                "shape": "dot",
                "size": 15,
                "color": {
                    "background": color,
                    "border": "#333"
                },
		    "font": {
		        "size": 10  # size font del nodo 10
                    }
            })

        edges = []
        for u, v, data in self.G.edges(data=True):
            edges.append({
                "id": f"{u}_{v}_{data['tx_id']}",
                "from": u,
                "to": v,
                "arrows": "to",
                "label": "",
                "originalLabel": "",
                "font": {
                	"size": 2,
                	"style": "italic",
                	"color": "blue"
                },
                "title": f"TxID: {data['tx_id'][:6]}\n{data['value']} BTC\nFecha: {data['date']}",                
                "color": {"color": "#999"},
                "width": 1,
                "value": data["value"],
                "date": data["date"],
                "tx_id": data["tx_id"]  
            })
            
            
      
            

        # (es demasiado larga para repetir completa en esta seccion) "align": "middle"
        # "label": f"{data['value']} BTC\n{data['tx_id'][:10]}...", 

        
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Blockchain Visual</title>
  <script src="https://unpkg.com/vis-network@9.1.2/dist/vis-network.min.js"></script>
  <link href="https://unpkg.com/vis-network@9.1.2/styles/vis-network.min.css" rel="stylesheet" />
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 20px;
    }}
    .legend {{
      margin-bottom: 1em;
    }}
    .dot {{
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      margin-right: 8px;
    }}
    #layout {{
      display: flex;
      flex-direction: row;
      gap: 20px;
    }}
    #left-panel {{
      flex: 2;  /* Reducir el tamano del panel izquierdo donde se muestra el grafo */
    }}
    #right-panel {{
      flex: 1;  /* Ampliar el panel derecho donde se muestra la tabla de transacciones */
      max-height: 80vh;  /* Limitar la altura maxima del panel derecho */
      width: 40%;
      overflow-y: auto;
    }}
    #network {{
      width: 100%;
      height: 60vh;  /* Reducir la altura del area de grafo */
      border: 1px solid lightgray;
    }}
    #infoTable {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}
    #infoTable th, #infoTable td {{
      border: 1px solid #ccc;
      padding: 6px;
      font-size: 14px; /*14px;*/
    }}
    #infoTable th {{
      background-color: #f0f0f0;
    }}
    #resetButton {{
      margin-top: 10px;
      padding: 10px;
      background-color: #4CAF50;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
    }}
    #resetButton:hover {{
      background-color: #45a049;
    }}
    #exportCSVButton {{
      margin-top: 10px;
      padding: 10px;
      background-color: #4CAF50;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
    }}
    #exportCSVButton:hover {{
       background-color: #45a049;
    }}
  </style>
</head>
<body>
  <h2>Visualizacion de Transacciones Blockchain</h2>
  
<div id="globalGraphInfo" style="margin-bottom: 15px; font-weight: bold; font-size: 14px;"></div>

<!-- Panel informativo en columnas -->
<div style="display: flex; gap: 10px; margin-bottom: 10px;">
  <!-- Columna 1: Informacion del nodo -->
  <div style="flex: 2; border: 1px solid #ccc; padding: 10px; background-color: #f9f9f9;">
    <div id="selectedNodeInfo" style="font-size: 14px; "></div>
  </div>

    <div id="selectedNodeInfo" style="margin-bottom: 10px; font-weight: bold;"></div>
    <!--label><input type="checkbox" id="toggleNodeLabels" checked> Mostrar etiquetas de nodos</label-->

  <!-- Columna 2: Leyenda -->
  <div style="flex: 1; border: 1px solid #ccc; padding: 8px; background-color: #f9f9f9;">
    <strong>Leyenda Nodos:</strong>
    <ul>
      <span class="dot" style="background-color:#FF6B6B;"></span> Emisor<br>
      <span class="dot" style="background-color:#66BB6A;"></span> Receptor<br>
      <span class="dot" style="background-color:#FFA726;"></span> Mixto<br>
    </ul>
    <strong>Leyenda Aristas:</strong>
    <ul>
      <span class="dot" style="background-color:#d33;"></span> Saliente<br>
      <span class="dot" style="background-color:#2e7d32;"></span> Entrante<br>
    </ul>
  </div>
</div>



  <!-- Checkbox para mostrar/ocultar etiquetas -->
  <div style="margin-bottom:10px;">
    <!--input type="checkbox" id="toggleLabels" checked -->
    <!--label for="toggleLabels">Mostrar etiquetas de nodos y transacciones</label -->
    
    <!--div id="selectedNodeInfo" style="margin-bottom: 10px; font-weight: bold;"></div-->
    <label><input type="checkbox" id="toggleNodeLabels" checked> Mostrar etiquetas de nodos</label>
  </div>
  
  
  <div id="layout">
    <div id="left-panel">
      <div id="network"></div>
    </div>
    <div id="right-panel">
      <h3>Transacciones del nodo seleccionado</h3>
      <table id="infoTable" style="display:none;">
        <thead>
          <tr>
            <th>ID Transaccion</th>
            <th>Emisor</th>
            <th>Receptor</th>
            <th>Valor</th>
            <th>Fecha</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
      <!-- Boton para resetear la seleccion -->
      <button id="resetButton">Resetear Seleccion</button>
      <button id="exportCSVButton">Exportar a CSV</button>
    </div>
  </div>

  <script>
    const allNodes = new vis.DataSet({json.dumps(nodes)});
    const allEdges = new vis.DataSet({json.dumps(edges)});
    const edges = new vis.DataSet(allEdges.get());
    const nodes = new vis.DataSet(allNodes.get());

    const container = document.getElementById("network");
    const network = new vis.Network(container, {{
      nodes: nodes,
      edges: edges
    }}, {{
      layout: {{ improvedLayout: true }},
      interaction: {{ tooltipDelay: 200 }},
      physics: {{ stabilization: true }}
    }});
    
   // totales  
   document.getElementById("globalGraphInfo").innerText = `Total de nodos: ${{nodes.length}}, Total de transacciones: ${{edges.length}}`;

    let lastSelectedNode = null;
    let lastSelectedEdge = null;

    network.on("selectNode", function(params) {{
      const selectedNode = params.nodes[0];
      
      // Restaurar conjunto completo antes de aplicar filtro
      edges.clear();
      edges.add(allEdges.get());

      // Si se selecciona dos veces el mismo nodo, restaurar todo
      if (selectedNode === lastSelectedNode) {{
        //edges.clear();
        //edges.add(allEdges.get());
        
        //lastSelectedNode = null;
        document.getElementById("infoTable").style.display = "none";
        document.getElementById("tableBody").innerHTML = "";
        document.getElementById("selectedNodeInfo").innerText = "";  // Limpiar label
        lastSelectedNode = null;
        return;
      }}
      
      lastSelectedNode = selectedNode;

      // Restaurar conjunto completo antes de aplicar filtro
      //edges.clear();
      //edges.add(allEdges.get());
      // ------------------------
      
      
      const connectedEdges = allEdges.get().filter(edge =>
        edge.from === selectedNode || edge.to === selectedNode
      ).map(edge => {{
        edge.color = {{
          color: edge.from === selectedNode ? "#d33" : "#2e7d32"
        }};
        edge.width = 2;
        return edge;
      }});

      edges.clear();
      edges.add(connectedEdges);

// TABLA DE TRANSACCIONES  -- Obtener conexiones de entrada y salida
const incomingEdges = connectedEdges.filter(edge => edge.to === selectedNode);
const outgoingEdges = connectedEdges.filter(edge => edge.from === selectedNode);

const incomingSummary = incomingEdges.map(edge =>
  `${{edge.from.slice(0, 6)}}...${{edge.from.slice(-4)}} (${{edge.value}} BTC)`
);
const outgoingSummary = outgoingEdges.map(edge =>
  `${{edge.to.slice(0, 6)}}...${{edge.to.slice(-4)}} (${{edge.value}} BTC)`
);

  const totalOutgoingValue = outgoingEdges.reduce((sum, edge) => sum + (parseFloat(edge.value) || 0), 0);
  const totalIncomingValue = incomingEdges.reduce((sum, edge) => sum + (parseFloat(edge.value) || 0), 0);

// Formato HTML en columnas
const nodeInfo = `
  <div style="display: flex; justify-content: space-between; font-size: 14px;">
    <div style="flex: 1;padding-right: 10px;">
      <strong>Tx desde:</strong><br><br>
      <li>${{incomingSummary.join("<br><li>")}}<br><br>
      <em><strong>${{incomingEdges.length}} transacciones entrantes</strong></em>
    </div>
    <div style="flex: 1;padding-right: 10px;">
      <strong>Nodo:</strong><br><br><br>
      <li>${{selectedNode.slice(0, 6)}}...${{selectedNode.slice(-4)}}
    </div>
    <div style="flex: 1;padding-left: 10px;">
      <strong>Tx hacia:</strong><br><br>
      <li>${{outgoingSummary.join("<br><li>")}}<br><br>
      <em><strong>${{outgoingEdges.length}} transacciones salientes</strong></em>
    </div>
  </div>
  <div style="text-align: center; margin-top: 10px; font-size: 12px;">
    <strong>Total de transacciones:</strong> ${{connectedEdges.length}}
  </div>
`;


  document.getElementById("selectedNodeInfo").innerHTML = nodeInfo;

      const tableBody = document.getElementById("tableBody");
      tableBody.innerHTML = "";
      //   <td>${{edge.tx_id}}</td>
      connectedEdges.forEach(edge => {{
        const row = document.createElement("tr");
        const shorTx_id = edge.tx_id.slice(0, 5) + "..." + edge.tx_id.slice(-2);
        row.innerHTML = `
          <td>${{edge.tx_id.slice(0, 6)}}...${{edge.tx_id.slice(-3)}}</td>
          <td>${{edge.from.slice(0, 6)}}...${{edge.from.slice(-3)}}</td>
          <td>${{edge.to.slice(0, 6)}}...${{edge.to.slice(-3)}}</td>
          <td>${{edge.value}} BTC</td>
          <td>${{edge.date}}</td>
        `;
        tableBody.appendChild(row);
      }});
      
      bindWalletLinks();  // Necesario para enlazar los nuevos links
      document.getElementById("infoTable").style.display = "table";
    }});

    network.on("selectEdge", function(params) {{
      const selectedEdge = params.edges[0];

      if (selectedEdge === lastSelectedEdge) {{
        // Si el mismo arco se selecciona dos veces, restaurar todo
        edges.clear();
        edges.add(allEdges.get());
        document.getElementById("infoTable").style.display = "none";
        document.getElementById("tableBody").innerHTML = "";
        lastSelectedEdge = null;
        return;
      }}

      lastSelectedEdge = selectedEdge;

      const selectedTransaction = allEdges.get(selectedEdge);

      // Mostrar informacion del arco seleccionado  //<td>${{selectedTransaction.tx_id}}</td>
      const tableBody = document.getElementById("tableBody");
      tableBody.innerHTML = "";
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${{selectedTransaction.tx_id.slice(0, 6)}}...${{selectedTransaction.tx_id.slice(-3)}}</td>
        <td>${{selectedTransaction.from.slice(0, 6)}}...${{selectedTransaction.from.slice(-3)}}</td>
        <td>${{selectedTransaction.to.slice(0, 6)}}...${{selectedTransaction.to.slice(-3)}}</td>
        <td>${{selectedTransaction.value}} BTC</td>
        <td>${{selectedTransaction.date}}</td>
      `;
      tableBody.appendChild(row);
      document.getElementById("infoTable").style.display = "table";
    }});

    // Funcion para resetear la seleccion y mostrar todos los arcos
    document.getElementById("resetButton").addEventListener("click", function() {{
      lastSelectedNode = null;
      lastSelectedEdge = null;
      edges.clear();
      edges.add(allEdges.get());
      document.getElementById("infoTable").style.display = "none";
      document.getElementById("tableBody").innerHTML = "";
      document.getElementById("selectedNodeInfo").innerText = "";  // Limpiar info al resetear
      //lastSelectedNode = null;
      //lastSelectedEdge = null;
    }});
    
    
let nodeLabelsVisible = true;
let edgeLabelsVisible = false;    
  
  document.getElementById("toggleNodeLabels").addEventListener("change", function () {{
    const showNodeLabels = this.checked;
    nodeLabelsVisible = this.checked;

    const updatedNodes = allNodes.get().map(node => ({{
            id: node.id, 
            label: showNodeLabels ? node.originalLabel : ''
        }})
    );
    nodes.update(updatedNodes);
}});






function bindWalletLinks() {{
  document.querySelectorAll(".wallet-link").forEach(link => {{
    link.addEventListener("click", function (e) {{
      e.preventDefault();
      const wallet = this.dataset.wallet;
      analyzeWallet(wallet); // Ya esta definida mas abajo
    }});
  }});
}}

document.body.addEventListener("click", function (e) {{
  if (e.target.classList.contains("wallet-link")) {{
    e.preventDefault();
    const wallet = e.target.dataset.wallet;
    analyzeWallet(wallet);
  }}
}});



	// Funcionalidad para exportar la tabla a CSV


    document.getElementById("exportCSVButton").addEventListener("click", function (e) {{
      console.log("boton pulsado");
      alert ("boton pulsado");
      e.preventDefault();
      const table = document.getElementById("infoTable");
      const rows = table.querySelectorAll("tbody tr");
      
      console.log("filas encontradas:", rows.length);
      
      if (!rows || rows.length === 0) {{
        alert("No hay transacciones para exportar.");
        return;
      }}
      let csvContent = "";
      //const headers = Array.from(rows[0].querySelectorAll("thead th")).map(th => `"${{th.textContent.trim()}}"`);
      const headers = Array.from(document.querySelectorAll("#infoTable thead th")).map(th => `"${{th.textContent.trim()}}"`);
      csvContent += headers.join(",") + "\\n";
      for (let i = 0; i < rows.length; i++) {{
        const row = Array.from(rows[i].querySelectorAll("td")).map(td => `"${{td.textContent.trim()}}"`);
        csvContent += row.join(",") + "\\n";
      }}
      const blob = new Blob([csvContent], {{ type: "text/csv;charset=utf-8;" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", "transacciones.csv");
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }});


   
  </script>
</body>
</html>
"""

        
   
            
            
            
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)






def main():
    """
    Punto de entrada principal. Lee configuracion desde 'config.ini',
    construye el grafo y guarda el resultado:
    - Si Depth >= 3: solo exporta GraphML.
    - Si Depth < 3: exporta HTML interactivo.
    """
    config = configparser.ConfigParser()

    try:
        config.read('config.ini')
        target = config['DEFAULT']['Target']
        max_depth = int(config['DEFAULT'].get('Depth', '0'))

        if not (len(target) == 34 or len(target) == 62):
            raise ValueError("Formato de target invalido. Debe ser direccion (34 caracteres) o hash (62)")

        analyzer = BlockchainAnalyzer()
        analyzer.build_graph(target, max_depth)

        if max_depth >= 3:
            analyzer.save_graphml('graph.graphml')
        else:
            analyzer.save_graphml('graph.graphml')
            analyzer.save_html_graph('transactions.html')
            print("Grafo HTML generado exitosamente en transactions.html")

    except KeyError as e:
        print(f"Error en config.ini: Falta la clave {e}")
    except ValueError as e:
        print(f"Error de entrada: {e}")
    except sqlite3.Error as e:
        print(f"Error de base de datos: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    main()

