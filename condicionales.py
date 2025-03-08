#aca miraremos los condicionales para python

a = int(input("digita un numero de 0 a 10"))
    
if a > 5:
    print("el numero es mayor a 5")
elif a == 5:
    print("el numero es igual a 5")
else:
    print("el numero es menor a 5")

#otro ejemplo
b = int(input("digita un numero de 0 a 10"))

if b > 5:
    print("el numero es mayor a 5")
else:
    if b == 5:
        print("el numero es igual a 5")
    else:
        print("el numero es menor a 5")

x = 5
if x>5:
    print("x es mayor a 5")
elif x == 5:
    print("x es igual a 5")
else:
    print("x es menor a 5")

#otro ejemplo
x = 15
y = 20

if x>10 and y>25:
    print("x es mayor a y and y es mayor a 25")

