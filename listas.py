to_do = ["Dirgirnos al hotel",
         "Hacer el check-in",
         "Dejar las maletas en la habitación",
         "Descansar un poco",
         "Salir a cenar"]
print(to_do)
numeros = [1, 2, 3, 4, 'cinco']
print(type(numeros))
mix = ['uno', 2, 3.14, True, {'nombre': 'Juan', 'edad': 25}]
print(mix)
print(type(mix))

print(len(to_do))
print(len(numeros))
print(len(mix))

print(to_do[0])
print(to_do[1])
print(to_do[2])
print(to_do[-1])
print(to_do[-2])

print(numeros[0])
print(numeros[1])
print(numeros[-1])

print(mix[0])
print(mix[1])
print(mix[-1])

print(to_do[1:3])
print(to_do[:2])
print(to_do[2:])

mix.append(False)
