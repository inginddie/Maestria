# aca veremos como son los numeros en python
x = 10
print(type(x)) #aca vemos la clase de la variable x como int que significa INTEGER o numero entero
Y = 10.5465
print(type(Y)) #aca vemos la clase de la variable Y como float que significa numero decimal
z = 1.2e3 # con la e se puede hacer notación cientifica en este caso al imprmir z se vera 1200.0
print(z) #imprime 1200.0
a = 1.2e-3 # con la e se puede hacer notación cientifica en este caso al imprmir a se vera 0.0012
print(a) #imprime 0.0012

#operaciones con numeros
#suma
x = 10
y = 20
print(x + y) #imprime 30
#resta
print(x - y) #imprime -10

#booleanos datos en cambios de estado
is_true = True
is_false = False
print(type(is_true)) #imprime <class 'bool'> que significa booleano
print(type(is_false)) #imprime <class 'bool'> que significa booleano

#operadores de comparación
b = 10
c = 3
print('Suma:', b + c) #imprime 13
print('Resta:', b - c) #imprime 7
print('Multiplicación:', b * c) #imprime 30
print('División:', b / c) #imprime 3.3333333333333335
print('División entera:', b // c) #imprime 3
print('Módulo:', b % c) #imprime 1 que es el residuo de la división
print('Potencia:', b ** c) #imprime 1000 que es 10^3

#shortcuts
#suma
x = 10
x += 5 #es lo mismo que x = x + 5
print(x) #imprime 15
#resta
x = 10
x -= 5 #es lo mismo que x = x - 5
print(x) #imprime 5
#multiplicación
x = 10
x *= 5 #es lo mismo que x = x * 5
print(x) #imprime 50
#división
x = 10
x /= 5 #es lo mismo que x = x / 5
print(x) #imprime 2.0
#división entera
x = 10
x //= 5 #es lo mismo que x = x // 5
print(x) #imprime 2
#módulo
x = 10
x %= 5 #es lo mismo que x = x % 5
print(x) #imprime 0
#potencia
x = 10
x **= 5 #es lo mismo que x = x ** 5
print(x) #imprime 100000

#operadores de comparación
#igualdad
x = 10
y = 20
print(x == y) #imprime False
#diferencia
print(x != y) #imprime True
#mayor que
print(x > y) #imprime False
#menor que
print(x < y) #imprime True
#mayor o igual que

#pemdas
#lo que significa pemndas es P=parentesis E=exponentes M=multiplicación D=división A=adición S=sustracción
#se debe seguir el orden de las operaciones para que el resultado sea el correcto
#siempre se debe hacer primero las operaciones de parentesis
#luego las de exponentes
#luego las de multiplicación y división
#y por ultimo las de adición y sustracción
operation1 = 2 + 3 * 5 + 4
print(operation1) #imprime 21
operation2 = (2 + 3) * 5
print(operation2) #imprime 25
operation3 =(2+3) * (4**2)/ 8-1
print(operation3) #imprime 10.0

# input
nombre = input("Ingresa tu nombre: ")
print(f"Hola, {nombre}")

