"""
Gestor de configuración basado en config.ini.
"""
import configparser
import os


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "..", "config.ini")


class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self._cargar()

    def _cargar(self):
        if os.path.exists(CONFIG_PATH):
            self.config.read(CONFIG_PATH, encoding="utf-8")
        else:
            self._crear_defecto()

    def _crear_defecto(self):
        self.config["database"] = {"path": "pmp_data.db"}
        self.config["app"] = {"idioma": "es", "tema": "industrial"}
        self.guardar()

    def guardar(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            self.config.write(f)

    def get(self, seccion: str, clave: str, fallback=None):
        return self.config.get(seccion, clave, fallback=fallback)

    def set(self, seccion: str, clave: str, valor: str):
        if not self.config.has_section(seccion):
            self.config.add_section(seccion)
        self.config.set(seccion, clave, valor)
        self.guardar()
