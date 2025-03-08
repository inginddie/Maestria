# Vamos aprender a crear variebles en python
# Siempre debe estar ('') o ("") para que funcione el print
saludo = "hola soy diego y voy aprender python"
Nombre = "Diego"
print(saludo)
print('Nombre:', Nombre)

# Variables manipulación de cadena de texto

Nombre2 = "Arturo"
print(type(Nombre2))
#al imprimir el tipo de variable se puede ver que es un string(str)
caracter = 'c'
print(type(caracter)) #al imprimir el tipo de variable se puede ver que es un string(str)

# variables con 3 comillas
x = '''hola

mundo''' #cuando se utiliza 3 comillas se puede escribir en varias lineas y respeta los saltos de linea
print(x)

# indexación de cadenas de texto 
# Python cuenta desde 0
indexacion = 'Diego Bustos'
print(indexacion[0]) #imprime la letra D
print(indexacion[1]) #imprime la letra i
print(indexacion[2]) #imprime la letra e
print(indexacion[3]) #imprime la letra g    
print(indexacion[4]) #imprime la letra o
print(indexacion[5]) #imprime un espacio
print(indexacion[6]) #imprime la letra B
print(indexacion[7]) #imprime la letra u
print(indexacion[8]) #imprime la letra s
print(indexacion[9]) #imprime la letra t
print(indexacion[10]) #imprime la letra o
print(indexacion[11]) #imprime la letra s

#indexación negativa
print(indexacion[-1]) #imprime la letra s
print(indexacion[-2]) #imprime la letra o
print(indexacion[-3]) #imprime la letra t
#asi se puede ir de atras hacia adelante

#cadenas de texto
primer_nombre = 'Diego'
segundo_nombre = 'Arturo'
apellido = 'Bustos'
print(primer_nombre + ' ' + segundo_nombre + ' ' + apellido) #concatenación de cadenas de texto

#replicación de cadenas de texto
print(primer_nombre * 3) #imprime 3 veces Diego

#longitud de una cadena de texto
print(len(primer_nombre)) #imprime 5
#len ayuda a saber cuantos caracteres tiene una cadena de texto

#metodos de cadenas de texto
#metodo lower
print(primer_nombre.lower()) #imprime diego en minusculas si deja uno en MAY

#metodo upper
print(primer_nombre.upper()) #imprime DIEGO en MAY si deja uno en minusculas

#metodo strip
espacios = '     hola     ' #elimina los espacios en blanco al principio y al final de la cadena de texto
print(espacios.strip()) #imprime hola sin los espacios en blanco
