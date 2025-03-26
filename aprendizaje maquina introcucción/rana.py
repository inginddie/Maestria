#En este juego el estado inicial se define como una secuencia de cuadrados con `N` ranas azules a la izquierda, luego un cuadrado vacío y luego `N` ranas de color rojo a la derecha. La figura presenta un ejemplo para `N=2`. Representaremos el estado del juego como la cadena `'AA.RR'`. El objetivo es intercambiar las piezas, llegando al estado `'RR.AA'`. Una pieza `'A'` se mueve de izquierda a derecha, ya sea deslizándose un espacio hacia adelante cuando el siguiente espacio está vacío, o se mueve dos espacios hacia adelante si el segundo espacio está vacío y hay una `'R'` en el medio para saltar. Las piezas `'R'` se mueven de derecha a izquierda de la misma forma. En este caso, definiremos una acción como una pareja `(i, j)` que representa intercambiar las piezas en esas posiciones. Por ejemplo, Las acciones disponibles para el estado presentado en la figura serán: `{(1, 2), (3, 2)}`. La rana azul en la posición `1` o la rana roja en la posición `3` pueden intercambiar lugares con el espacio en blanco en la posición `2`.

# Solución propuesta

class Tablero:
    def __init__(self, estado, padre=None, accion=None, costo=1):
        self.estado = estado
        self.padre = padre
        self.accion = accion
        self.costo = costo # Add this line to define the 'costo' attribute

    def __repr__(self):
        return ' '.join(self.estado) + '\n'

    def __lt__(self, other):
        return self.costo < other.costo # Now you can access self.costo here
from collections import deque

class Problema:
    def __init__(self, estado_inicial, estado_objetivo):
        self.estado_inicial = Tablero(estado_inicial)
        self.estado_objetivo = estado_objetivo

    def acciones(self, nodo):
        index = nodo.estado.index('_')
        movimientos = []

        if index > 0 and nodo.estado[index - 1] == 'A':
            movimientos.append(f"{index - 1} -> {index}")  # Movimiento normal

        if index > 1 and nodo.estado[index - 2] == 'A' and nodo.estado[index - 1] == 'R':
            movimientos.append(f"{index - 2} -> {index}")  # Salto sobre 'R'

        if index < 4 and nodo.estado[index + 1] == 'R':
            movimientos.append(f"{index + 1} -> {index}")  # Movimiento normal

        if index < 3 and nodo.estado[index + 2] == 'R' and nodo.estado[index + 1] == 'A':
            movimientos.append(f"{index + 2} -> {index}")  # Salto sobre 'A'

        return movimientos

    #The methods "resultado" and "es_objetivo" are now correctly indented within the "Problema" class

    def resultado(self, nodo, accion):
        estado = list(nodo.estado)
        index1, index2 = map(int, accion.split(" -> "))
        estado[index1], estado[index2] = estado[index2], estado[index1]
        return Tablero("".join(estado), padre=nodo, accion=accion, costo=nodo.costo + 1)#Se agrega el retorno del costo
    def es_objetivo(self, nodo):
        return nodo.estado == self.estado_objetivo
    def heuristica(nodo, problema):
        return sum(1 for i in range(len(nodo.estado)) if nodo.estado[i] != problema.estado_objetivo[i])#cuántas posiciones difieren entre el estado actual y el objetivo.
def heuristica(nodo, problema):#esta heuristica me la dio como opción con Chat GPT
    distancia = 0
    for i, letra in enumerate(nodo.estado):
        pos_correcta = problema.estado_objetivo.index(letra)  # Encuentra la posición correcta de la letra
        distancia += abs(i - pos_correcta)  # Calcula la distancia entre su posición actual y la correcta
    return distancia
def expandir(nodo, problema):
    """Expande un nodo dado para expandir todos sus hijos (ramas)"""
    hijos = []

    #bucle sobre cada accion posible que se pueda hacer en este nodo
    for accion in problema.acciones(nodo):

        hijo = problema.resultado(nodo, accion)
        hijos.append(hijo)

    return hijos

def UCS(problema):
    frontera = []
    heapq.heappush(frontera, (0, problema.estado_inicial))
    cerrados = set()
    while frontera:
        _, nodo = heapq.heappop(frontera)
        if problema.es_objetivo(nodo):
            return nodo
        if nodo.estado not in cerrados:
            cerrados.add(nodo.estado)
            for hijo in expandir(nodo, problema):
                if hijo.estado not in cerrados:
                    heapq.heappush(frontera, (hijo.costo, hijo))
    return "FAILURE"

def voraz(problema):
    frontera = []
    heapq.heappush(frontera, (heuristica(problema.estado_inicial, problema), problema.estado_inicial))
    cerrados = set()
    while frontera:
        _, nodo = heapq.heappop(frontera)
        if problema.es_objetivo(nodo):
            return nodo
        if nodo.estado not in cerrados:
            cerrados.add(nodo.estado)
            for hijo in expandir(nodo, problema):
                if hijo.estado not in cerrados:
                    heapq.heappush(frontera, (heuristica(hijo, problema), hijo))
    return "FAILURE"

def A_estrella(problema):
    frontera = []
    heapq.heappush(frontera, (0, problema.estado_inicial))
    cerrados = set()
    while frontera:
        _, nodo = heapq.heappop(frontera)
        if problema.es_objetivo(nodo):
            return nodo
        if nodo.estado not in cerrados:
            cerrados.add(nodo.estado)
            for hijo in expandir(nodo, problema):
                if hijo.estado not in cerrados:
                    f = hijo.costo + heuristica(hijo, problema)
                    heapq.heappush(frontera, (f, hijo))
    return "FAILURE"

def estados_camino(nodo):
    """Me devuelve el camino de estados desde el nodo inicial hasta el nodo objetivo."""
    camino = []

    while nodo:

        camino.append(nodo.estado)
        nodo = nodo.padre


    camino.reverse()
    return camino

def acciones_camino(nodo):
    """Me devuelve el camino de acciones desde el nodo inicial hasta el nodo objetivo."""
    camino = []
    while nodo and nodo.accion is not None:
        # Agrega la acción actual al camino
        camino.append(nodo.accion)
        nodo = nodo.padre
    # Invierte el camino para que empiece desde el estado inicial
    camino.reverse()
    return camino
def main():
    estado_inicial = "AA_RR"
    estado_objetivo = "RR_AA"
    problema = Problema(estado_inicial, estado_objetivo)

    print("\nResolviendo con UCS...")
    solucion = UCS(problema)
    if solucion != "FAILURE":
        print("Estados en el camino con UCS:")
        for estado in estados_camino(solucion):
            print(Tablero(estado))
    else:
        print("UCS: No se encontró solución.")

    print("\nResolviendo con Voraz...")
    solucion = voraz(problema)
    if solucion != "FAILURE":
        print("Estados en el camino con Voraz:")
        for estado in estados_camino(solucion):
            print(Tablero(estado))
    else:
        print("Voraz: No se encontró solución.")

    print("\nResolviendo con A*...")
    solucion = A_estrella(problema)
    if solucion != "FAILURE":
        print("Estados en el camino con A*:")
        for estado in estados_camino(solucion):
            print(Tablero(estado))
    else:
        print("A*: No se encontró solución.")

if __name__ == "__main__":
    main()
