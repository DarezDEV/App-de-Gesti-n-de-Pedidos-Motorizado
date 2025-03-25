class Bateria:
    def __init__(self, tipo, tamaño, capacidad_carga, marca):
        self.tipo = tipo
        self.tamaño = tamaño
        self.capacidad_carga = capacidad_carga
        self.marca = marca

    def Cargarse(self):
        print(f"La batería de marca {self.marca} y tipo {self.tipo} se está cargando...")


