"""
Modelo: Adjunto — Archivos vinculados a cualquier registro del sistema.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.models.base import Base


class Adjunto(Base):
    __tablename__ = "adjuntos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tabla_origen = Column(String(100), nullable=False)
    # Ej: 'equipos', 'ordenes_trabajo', 'materiales', 'trabajadores'
    registro_id = Column(Integer, nullable=False)
    nombre_archivo = Column(String(300), nullable=False)
    ruta_archivo = Column(String(500), nullable=False)
    tipo_archivo = Column(String(50), nullable=True)
    # Ej: 'imagen', 'pdf', 'documento', 'video'
    tamanio = Column(Integer, default=0)  # bytes
    descripcion = Column(String(300), nullable=True)
    fecha_subida = Column(DateTime, default=func.now())
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)

    def __repr__(self):
        return f"<Adjunto {self.tabla_origen}/{self.registro_id} - {self.nombre_archivo}>"
