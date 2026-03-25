"""
Modelos: Equipo, LecturaContador.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=True)
    ubicacion = Column(String(200), nullable=True)
    area = Column(String(150), nullable=True)
    centro_costo = Column(String(100), nullable=True)
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)
    serie = Column(String(100), unique=True, nullable=True)
    fabricante = Column(String(150), nullable=True)
    criticidad = Column(String(20), nullable=False, default="Media")
    # Criticidad: Crítica / Alta / Media / Baja
    fecha_alta = Column(DateTime, default=func.now())
    tipo_contador = Column(String(50), nullable=True)
    # Ej: "Horas", "Kilómetros", "Ciclos"
    lectura_inicial = Column(Float, default=0.0)
    lectura_actual = Column(Float, default=0.0)
    estado = Column(String(30), default="Activo")
    # Estados: Activo / Inactivo / Dado de baja / En mantenimiento
    costo_reposicion = Column(Float, default=0.0)
    observaciones = Column(Text, nullable=True)
    imagen_ruta = Column(String(500), nullable=True)
    fecha_actualizacion = Column(DateTime, onupdate=func.now())

    lecturas = relationship("LecturaContador", back_populates="equipo",
                            cascade="all, delete-orphan")
    ordenes = relationship("OrdenTrabajo", back_populates="equipo")
    planes = relationship("PlanMantenimiento", back_populates="equipo")
    historial = relationship("HistorialEquipo", back_populates="equipo")
    adjuntos = relationship("Adjunto",
                            primaryjoin="and_(Adjunto.tabla_origen=='equipos', "
                                        "foreign(Adjunto.registro_id)==Equipo.id)")

    def __repr__(self):
        return f"<Equipo {self.codigo} - {self.nombre}>"


class LecturaContador(Base):
    __tablename__ = "lecturas_contador"

    id = Column(Integer, primary_key=True, autoincrement=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    fecha = Column(DateTime, default=func.now())
    lectura = Column(Float, nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    observaciones = Column(String(300), nullable=True)

    equipo = relationship("Equipo", back_populates="lecturas")

    def __repr__(self):
        return f"<Lectura {self.equipo_id} - {self.lectura}>"
