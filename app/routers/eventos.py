from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EventoRecibido
from app.schemas import EventoEntrada, EventoRespuesta
from app.services.eventos import procesar_evento

router = APIRouter(prefix="/api/v1/eventos", tags=["eventos"])


@router.post("", response_model=EventoRespuesta)
def recibir_evento(entrada: EventoEntrada, db: Session = Depends(get_db)) -> EventoRespuesta:
    """Ingesta opcional para otros microservicios. El Frontend no consume este endpoint."""
    return procesar_evento(db, entrada)


@router.get("")
def listar_eventos(db: Session = Depends(get_db), limite: int = 30) -> dict:
    filas = db.query(EventoRecibido).order_by(EventoRecibido.id.desc()).limit(limite).all()
    return {
        "total_mostrado": len(filas),
        "eventos": [
            {
                "evento_id": fila.evento_id,
                "tipo": fila.tipo,
                "recibido_en": fila.recibido_en.isoformat() if fila.recibido_en else None,
            }
            for fila in filas
        ],
    }
