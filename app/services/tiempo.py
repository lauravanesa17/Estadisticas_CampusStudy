from datetime import datetime, timezone


ESTADOS_CERRADOS = {"completada", "cancelada"}
ALIAS_ESTADO = {
    "entregada": "completada",
    "completado": "completada",
}


def ahora() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hoy_iso() -> str:
    return ahora().date().isoformat()


def normalizar_estado(estado: object) -> str:
    texto = str(estado or "pendiente").strip().lower()
    return ALIAS_ESTADO.get(texto, texto or "pendiente")


def parsear_fecha(valor: object) -> datetime | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None) if valor.tzinfo else valor
    texto = str(valor).replace("Z", "+00:00")
    if len(texto) == 10 and texto[4] == "-" and texto[7] == "-":
        texto = f"{texto}T23:59:00"
    try:
        parsed = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def parsear_fecha_entrega(fecha: object, hora: object = None) -> datetime | None:
    if fecha is None or fecha == "":
        return None
    texto = str(fecha)
    if hora and "T" not in texto:
        hora_txt = str(hora)
        texto = f"{texto}T{hora_txt}:00" if len(hora_txt) == 5 else f"{texto}T{hora_txt}"
    return parsear_fecha(texto)


def estado_efectivo(estado: str, fecha_entrega: datetime | None, momento: datetime | None = None) -> str:
    """vencida es un conteo derivado: no es un estado persistido por tareas-service."""
    canonico = normalizar_estado(estado)
    if canonico in ESTADOS_CERRADOS:
        return canonico
    referencia = momento or ahora()
    if fecha_entrega and fecha_entrega.date() < referencia.date():
        return "vencida"
    return canonico or "pendiente"
