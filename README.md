# CampusStudy — Microservicio de Estadísticas

Servicio alineado con el **Contrato de Interfaz e Integración** del equipo Frontend (versión 1.0, `/api/v1/`).

No es dueño de usuarios, materias, tareas ni grupos. Consulta esos servicios cuando están disponibles, guarda una **caché local** y expone reportes agregados.

## Endpoints que consume el Frontend

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/estadisticas/usuario/{usuario_id}` | Reporte individual |
| GET | `/api/v1/estadisticas/materia/{materia_id}` | Reporte por materia |
| GET | `/api/v1/estadisticas/grupo/{grupo_id}` | Reporte por grupo |

Query opcionales en usuario: `periodo=YYYY-MM` y `materia_id`.

### Respuesta 200 — usuario (schema Zod)

```json
{
  "usuario_id": 25,
  "nombre": "Ana",
  "periodo": "2026-10",
  "tareas": {
    "total": 4,
    "completadas": 2,
    "pendientes": 1,
    "vencidas": 1,
    "porcentaje_completado": 50.0
  },
  "grupos": {
    "total_grupos": 2,
    "grupos_activos": 2
  },
  "materias": [
    { "materia_id": 4, "nombre": "Sistemas Distribuidos", "tareas_completadas": 1, "tareas_total": 2 }
  ],
  "fecha_calculo": "2026-10-12"
}
```

Reglas tomadas del contrato:

- IDs enteros positivos (`usuario_id`, no `usr-01`)
- `snake_case` en español
- fechas `YYYY-MM-DD`
- porcentajes con un decimal
- `vencida` es un **conteo derivado** (la tarea sigue en `pendiente` o `en_progreso` en Tareas)
- `en_progreso` se reporta dentro de `pendientes` para no romper el schema Zod del Frontend
- `cancelada` no entra en los totales

## Errores

```json
{ "codigo": 404, "mensaje": "Usuario no encontrado." }
```

| Código | Cuándo |
|---|---|
| 400 | Parámetro inválido |
| 404 | Usuario, materia o grupo no encontrado |
| 503 | Dependencia caída y sin caché |

Si hay caché y Tareas/Usuarios no responden, se sirve el último dato local (no se inventan ceros).

## Cómo ejecutarlo

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

- Dashboard de prueba: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

Al arrancar carga datos de demo (Ana = `usuario_id` 25) para poder mostrar el servicio sin los otros equipos.

Variables opcionales para consultar a los demás microservicios:

```
USUARIOS_SERVICE_URL=http://localhost:8001
MATERIAS_SERVICE_URL=http://localhost:8002
TAREAS_SERVICE_URL=http://localhost:8003
GRUPOS_SERVICE_URL=http://localhost:8004
```

Estadísticas llama, entre otros, a `GET /api/v1/tareas?usuario_id=` y `GET /api/v1/usuarios/{id}`.
