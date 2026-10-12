def _registrar_base(client):
    client.post("/api/v1/eventos", json={
        "evento_id": "u-25",
        "evento": "usuario.registrado",
        "payload": {"usuario_id": 25, "nombre": "Ana", "email": "ana@uniminuto.edu.co"},
    })
    client.post("/api/v1/eventos", json={
        "evento_id": "m-4",
        "evento": "materia.creada",
        "payload": {"materia_id": 4, "nombre": "Sistemas Distribuidos", "nrc": "12345"},
    })


def test_salud(client):
    respuesta = client.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["servicio"] == "estadisticas"


def test_reporte_usuario_cumple_contrato_frontend(client):
    _registrar_base(client)
    client.post("/api/v1/eventos", json={
        "evento_id": "t-15",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 15,
            "titulo": "Contrato de interfaz",
            "usuario_id": 25,
            "materia_id": 4,
            "fecha_entrega": "2026-12-01",
            "hora_entrega": "18:00",
            "estado": "completada",
        },
    })
    client.post("/api/v1/eventos", json={
        "evento_id": "t-16",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 16,
            "titulo": "Pendiente",
            "usuario_id": 25,
            "materia_id": 4,
            "fecha_entrega": "2026-12-20",
            "estado": "pendiente",
        },
    })

    respuesta = client.get("/api/v1/estadisticas/usuario/25")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario_id"] == 25
    assert isinstance(cuerpo["usuario_id"], int)
    assert cuerpo["nombre"] == "Ana"
    assert cuerpo["tareas"]["total"] == 2
    assert cuerpo["tareas"]["completadas"] == 1
    assert cuerpo["tareas"]["pendientes"] == 1
    assert cuerpo["tareas"]["vencidas"] == 0
    assert cuerpo["tareas"]["porcentaje_completado"] == 50.0
    assert cuerpo["materias"][0]["materia_id"] == 4
    assert cuerpo["materias"][0]["nombre"] == "Sistemas Distribuidos"
    assert "fecha_calculo" in cuerpo
    assert len(cuerpo["fecha_calculo"]) == 10


def test_tarea_vencida_es_conteo_derivado(client):
    _registrar_base(client)
    client.post("/api/v1/eventos", json={
        "evento_id": "t-vencida",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 99,
            "titulo": "Ya se venció",
            "usuario_id": 25,
            "materia_id": 4,
            "estado": "pendiente",
            "fecha_entrega": "2026-01-01",
        },
    })
    cuerpo = client.get("/api/v1/estadisticas/usuario/25").json()
    assert cuerpo["tareas"]["vencidas"] == 1
    assert cuerpo["tareas"]["pendientes"] == 0
    assert cuerpo["tareas"]["completadas"] == 0


def test_en_progreso_cuenta_como_pendiente_en_el_contrato_del_front(client):
    _registrar_base(client)
    client.post("/api/v1/eventos", json={
        "evento_id": "t-prog",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 40,
            "titulo": "En curso",
            "usuario_id": 25,
            "materia_id": 4,
            "estado": "en_progreso",
            "fecha_entrega": "2026-12-01",
        },
    })
    cuerpo = client.get("/api/v1/estadisticas/usuario/25").json()
    assert cuerpo["tareas"]["pendientes"] == 1
    assert "en_progreso" not in cuerpo["tareas"]


def test_idempotencia_de_eventos(client):
    _registrar_base(client)
    evento = {
        "evento_id": "mismo",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 70,
            "titulo": "Duplicada",
            "usuario_id": 25,
            "materia_id": 4,
            "estado": "pendiente",
            "fecha_entrega": "2026-12-01",
        },
    }
    primera = client.post("/api/v1/eventos", json=evento)
    segunda = client.post("/api/v1/eventos", json=evento)
    assert primera.json()["duplicado"] is False
    assert segunda.json()["duplicado"] is True
    assert client.get("/api/v1/estadisticas/usuario/25").json()["tareas"]["total"] == 1


def test_usuario_inexistente_404(client):
    respuesta = client.get("/api/v1/estadisticas/usuario/999")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == 404
    assert "mensaje" in respuesta.json()


def test_parametro_invalido_400(client):
    respuesta = client.get("/api/v1/estadisticas/usuario/abc")
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == 400


def test_filtro_materia_en_query(client):
    _registrar_base(client)
    client.post("/api/v1/eventos", json={
        "evento_id": "m-12",
        "evento": "materia.creada",
        "payload": {"materia_id": 12, "nombre": "Bases de Datos", "nrc": "30210"},
    })
    client.post("/api/v1/eventos", json={
        "evento_id": "t-a",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 1, "titulo": "A", "usuario_id": 25, "materia_id": 4,
            "estado": "completada", "fecha_entrega": "2026-12-01",
        },
    })
    client.post("/api/v1/eventos", json={
        "evento_id": "t-b",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 2, "titulo": "B", "usuario_id": 25, "materia_id": 12,
            "estado": "pendiente", "fecha_entrega": "2026-12-01",
        },
    })
    cuerpo = client.get("/api/v1/estadisticas/usuario/25?materia_id=4").json()
    assert cuerpo["tareas"]["total"] == 1
    assert cuerpo["materias"][0]["materia_id"] == 4


def test_reporte_grupo(client):
    _registrar_base(client)
    client.post("/api/v1/eventos", json={
        "evento_id": "g-7",
        "evento": "grupo.creado",
        "payload": {
            "grupo_id": 7,
            "nombre": "Grupo de estudio - Sistemas Distribuidos",
            "materia_id": 4,
            "creado_por": 25,
            "integrantes": [{"usuario_id": 25, "rol": "lider"}],
        },
    })
    client.post("/api/v1/eventos", json={
        "evento_id": "t-g",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 55,
            "titulo": "Grupal",
            "usuario_id": 25,
            "materia_id": 4,
            "grupo_id": 7,
            "estado": "completada",
            "fecha_entrega": "2026-10-10",
        },
    })
    cuerpo = client.get("/api/v1/estadisticas/grupo/7").json()
    assert cuerpo["grupo_id"] == 7
    assert cuerpo["integrantes"] == 1
    assert cuerpo["tareas"]["completadas"] == 1
