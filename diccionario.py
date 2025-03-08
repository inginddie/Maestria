numbers = {1: 'uno', 2: 'dos', 3: 'tres'}
print(numbers[2])
information = {'nombre': 'Juan',
                'edad': 25,
                'cursos': ['Python', 'Django', 'JavaScript']}
print(information['nombre'])
del information['edad']
print(information)
clave = information.keys()
values = information.values()
print(values)

#comprension de listas
squares = [x**2 for x in range(1,11)]
print("cuadrados: ", squares)

celsius = [0, 10, 20, 30, 40]
fahrenheit = [(temp * 9/5) + 32 for temp in celsius]
print("temperatura: ", fahrenheit)

#numeros pares
evens = [x for x in range(1, 21) if x % 2 == 0]
print("pares: ", evens)

#matrix
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
transposed =[[row[i] for row in matrix] for i in range(len(matrix[0]))]
print(transposed)
#otra forma de trasponer los datos de una matriz
transposed = []
for i in range(3):
    transposed.append([row[i] for row in matrix])
print(transposed)
