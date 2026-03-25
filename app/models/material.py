"""
Modelos: Material, MovimientoMaterial.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship
from app.models.base import Base


class Material(Base):
    __tablename__ = "materiales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(300), nullable=False)
    categoria = Column(String(100), nullable=True)
    unidad = Column(String(30), nullable=False, default="UN")
    stock_actual = Column(Float, default=0.0)
    stock_minimo = Column(Float, default=0.0)
    costo_unitario = Column(Float, default=0.0)
    proveedor = Column(String(200), nullable=True)
    ubicacion_almacen = Column(String(150), nullable=True)
    estado = Column(String(30), default="Activo")
    # Estados: Activo / Inactivo / Descontinuado
    criticidad = Column(String(20), default="Normal")
    # Criticidad: Crítico / Normal
    observaciones = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=func.now())

    movimientos = relationship("MovimientoMaterial", back_populates="material")

    @property
    def alerta_stock(self) -> str:
        """Retorna nivel de alerta: 'critico', 'bajo', 'normal'."""
        if self.criticidad == "Crítico" and self.stock_actual <= 0:
            return "critico"
        if self.stock_actual <= self.stock_minimo:
            return "bajo"
        return "normal"

    def __repr__(self):
        return f"<Material {self.codigo} - {self.descripcion}>"


class MovimientoMaterial(Base):
    __tablename__ = "movimientos_materiales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey("materiales.id"), nullable=False)
    tipo_movimiento = Column(String(30), nullable=False)
    # Tipos: Entrada / Salida / Ajuste / Consumo OT / Devolución
    cantidad = Column(Float, nullable=False)
    costo_unitario = Column(Float, default=0.0)
    ot_id = Column(Integer, ForeignKey("ordenes_trabajo.id"), nullable=True)
    motivo = Column(String(300), nullable=True)
    fecha = Column(DateTime, default=func.now())
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    stock_anterior = Column(Float, default=0.0)
    stock_posterior = Column(Float, default=0.0)

    material = relationship("Material", back_populates="movimientos")

    def __repr__(self):
        return f"<Movimiento {self.tipo_movimiento} {self.cantidad}>"
