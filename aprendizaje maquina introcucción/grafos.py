import networkx as nx
import matplotlib.pyplot as plt

# Función para dibujar un grafo o árbol con un camino resaltado
def draw_graph(G, pos, path=None, title="Grafo", node_color='lightblue', edge_color='black'):
    plt.figure(figsize=(10, 6))
    plt.title(title)
    
    # Dibujar nodos
    nx.draw_networkx_nodes(G, pos, node_color=node_color, node_size=1500)
    
    # Dibujar aristas
    edge_colors = [edge_color for u, v in G.edges()]
    if path:
        # Resaltar las aristas del camino en rojo
        for i in range(len(path) - 1):
            if (path[i], path[i + 1]) in G.edges():
                edge_idx = list(G.edges()).index((path[i], path[i + 1]))
                edge_colors[edge_idx] = 'red'
    
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=2)
    
    # Dibujar etiquetas de nodos
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    # Dibujar etiquetas de costos (si existen)
    if G.edges(data=True):  # Verificar si hay aristas con datos
        edge_labels = {}
        has_weights = False
        for u, v, d in G.edges(data=True):
            if 'weight' in d:
                edge_labels[(u, v)] = d['weight']
                has_weights = True
        if has_weights:
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    
    plt.axis('off')
    plt.show()

# 1. Ejercicio 1: BFS (Grafo sin pesos, busca camino más corto)
def create_bfs_graph():
    G = nx.DiGraph()
    edges = [
        ('S', 'A'), ('A', 'B'), ('A', 'D'), 
        ('B', 'C'), ('C', 'G'), ('D', 'G')
    ]
    G.add_edges_from(edges)
    
    # Posiciones para una disposición clara
    pos = {
        'S': (0, 2), 'A': (0, 1), 'B': (-1, 0), 'C': (-2, -1), 
        'D': (1, 0), 'G': (0, -1)
    }
    
    # Camino óptimo encontrado por BFS: S → A → D → G
    path_bfs = ['S', 'A', 'D', 'G']
    
    # Dibujar grafo original
    draw_graph(G, pos, title="Grafo Ejercicio 1 (BFS)")
    
    # Crear y dibujar árbol de búsqueda BFS
    bfs_tree = nx.DiGraph()
    bfs_tree.add_edges_from([('S', 'A'), ('A', 'B'), ('A', 'D'), ('B', 'C'), ('D', 'G')])
    draw_graph(bfs_tree, pos, path_bfs, title="Árbol de Búsqueda BFS (S → A → D → G)", node_color='lightgreen')

# 2. Ejercicio 2: DFS (Grafo sin pesos, busca en profundidad)
def create_dfs_graph():
    G = nx.DiGraph()
    edges = [
        ('S', 'A'), ('S', 'D'), ('A', 'B'), ('B', 'C'), 
        ('C', 'G'), ('D', 'G')
    ]
    G.add_edges_from(edges)
    
    # Posiciones para una disposición clara
    pos = {
        'S': (0, 2), 'A': (-1, 1), 'B': (-2, 0), 'C': (-3, -1), 
        'D': (1, 1), 'G': (0, 0)
    }
    
    # Camino encontrado por DFS: S → A → B → C → G
    path_dfs = ['S', 'A', 'B', 'C', 'G']
    
    # Dibujar grafo original
    draw_graph(G, pos, title="Grafo Ejercicio 2 (DFS)")
    
    # Crear y dibujar árbol de búsqueda DFS
    dfs_tree = nx.DiGraph()
    dfs_tree.add_edges_from([('S', 'A'), ('A', 'B'), ('B', 'C'), ('C', 'G')])
    draw_graph(dfs_tree, pos, path_dfs, title="Árbol de Búsqueda DFS (S → A → B → C → G)", node_color='lightgreen')

# 3. Ejercicio 3: UCS (Grafo con pesos, busca camino de menor costo)
def create_ucs_graph():
    G = nx.DiGraph()
    edges = [
        ('S', 'A', {'weight': 1}), ('S', 'D', {'weight': 5}),
        ('A', 'B', {'weight': 3}), ('B', 'C', {'weight': 1}),
        ('C', 'G', {'weight': 1}), ('D', 'G', {'weight': 5})
    ]
    G.add_edges_from(edges)
    
    # Posiciones para una disposición clara
    pos = {
        'S': (0, 2), 'A': (-1, 1), 'B': (-2, 0), 'C': (-3, -1), 
        'D': (1, 1), 'G': (0, 0)
    }
    
    # Camino óptimo encontrado por UCS: S → A → B → C → G (costo total: 6)
    path_ucs = ['S', 'A', 'B', 'C', 'G']
    
    # Dibujar grafo original
    draw_graph(G, pos, title="Grafo Ejercicio 3 (UCS)")
    
    # Crear y dibujar árbol de búsqueda UCS
    ucs_tree = nx.DiGraph()
    ucs_tree.add_edges_from([
        ('S', 'A', {'weight': 1}), ('A', 'B', {'weight': 3}), 
        ('B', 'C', {'weight': 1}), ('C', 'G', {'weight': 1}),
        ('S', 'D', {'weight': 5}), ('D', 'G', {'weight': 5})
    ])
    draw_graph(ucs_tree, pos, path_ucs, title="Árbol de Búsqueda UCS (S → A → B → C → G, Costo: 6)", node_color='lightgreen')

# Ejecutar las funciones para generar los gráficos
if __name__ == "__main__":
    create_bfs_graph()  # Ejercicio 1
    create_dfs_graph()  # Ejercicio 2
    create_ucs_graph()  # Ejercicio 3