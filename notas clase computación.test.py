import unittest
from notas_clase_computacion import vehiculos

class TestVehiculos(unittest.TestCase):
    def setUp(self):
        self.vehiculo = vehiculos("rojo", "chevrolet", "2019", "abc123")

if __name__ == '__main__':
    unittest.main()
