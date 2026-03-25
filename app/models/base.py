"""
Base declarativa de SQLAlchemy y modelos comunes.
"""
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func


class Base(DeclarativeBase):
    pass


class ConfiguracionSistema(Base):
    __tablename__ = "configuraciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clave = Column(String(100), unique=True, nullable=False)
    valor = Column(String(500), nullable=True)
    descripcion = Column(String(300), nullable=True)
    tipo_dato = Column(String(20), default="str")  # str, int, float, bool

    def __repr__(self):
        return f"<Config {self.clave}={self.valor}>"


class BackupRegistrado(Base):
    __tablename__ = "backups_registrados"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_hora = Column(DateTime, default=func.now())
    ruta_archivo = Column(String(500))
    tamanio = Column(Integer, default=0)
    usuario_id = Column(Integer, nullable=True)
    tipo_backup = Column(String(50), default="manual")
    exitoso = Column(Boolean, default=True)
    observaciones = Column(String(500), nullable=True)
