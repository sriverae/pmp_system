"""
Modelo: Auditoria — Bitácora de todas las acciones del sistema.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    username = Column(String(100), nullable=True)  # Guardado por si el usuario se elimina
    fecha_hora = Column(DateTime, default=func.now())
    modulo = Column(String(100), nullable=False)
    accion = Column(String(100), nullable=False)
    tabla_afectada = Column(String(100), nullable=True)
    registro_id = Column(Integer, nullable=True)
    valor_anterior = Column(Text, nullable=True)
    valor_nuevo = Column(Text, nullable=True)
    observacion = Column(String(500), nullable=True)
    ip_origen = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<Auditoria {self.modulo}/{self.accion} por {self.username}>"
