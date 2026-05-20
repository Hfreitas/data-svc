from src.config import Config


FEEDBACK_FAKE = {
    "id": 1,
    "usuario_id": 1,
    "texto": "Achei o registro de vendas lento",
    "classificacao": "Agente 3 — Contador",
    "resolvido": False,
    "acao_tomada": None,
    "created_at": "2026-05-01T10:00:00+00:00",
}

RESUMO_FAKE = {
    "id": 1,
    "mes_referencia": "2026-05-01",
    "total_feedbacks": 10,
    "resolvidos_na_hora": 4,
    "payload_resumo": "Resumo do mês de maio",
    "created_at": "2026-06-01T00:00:00+00:00",
}


class TestPostFeedbackFlat:
    def test_salva_feedback_com_payload_completo(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.feedbacks.get_db_conn")
        insert_mock = mocker.patch("src.routes.feedbacks.queries.insert_feedback", return_value=FEEDBACK_FAKE)
        invalidate_mock = mocker.patch("src.routes.feedbacks.cache_invalidate_prefix")

        payload = {
            "usuario_id": 1,
            "texto": "Achei o registro de vendas lento",
            "classificacao": "Agente 3 — Contador",
            "resolvido": False,
            "acao_tomada": None,
        }
        resp = client.post("/feedbacks", json=payload)

        assert resp.status_code == 201
        assert resp.get_json() == FEEDBACK_FAKE
        insert_mock.assert_called_once_with(conn, 1, payload)
        invalidate_mock.assert_called_once_with("feedbacks", "1:")

    def test_retorna_400_sem_usuario_id(self, client):
        resp = client.post("/feedbacks", json={"texto": "bom"})

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing_field"

    def test_retorna_400_sem_texto(self, client):
        resp = client.post("/feedbacks", json={"usuario_id": 1})

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing_field"

    def test_retorna_400_classificacao_invalida(self, client):
        resp = client.post("/feedbacks", json={
            "usuario_id": 1,
            "texto": "bom",
            "classificacao": "bug",
        })

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "invalid_classificacao"

    def test_aceita_todas_classificacoes_validas(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.feedbacks.get_db_conn")
        mocker.patch("src.routes.feedbacks.queries.insert_feedback", return_value=FEEDBACK_FAKE)
        mocker.patch("src.routes.feedbacks.cache_invalidate_prefix")

        classificacoes = [
            "Agente 2 — Onboarding",
            "Agente 3 — Contador",
            "Agente 4 — Business",
            "Agente 5 — Agenda",
            "Agente 6 — Pagamento",
            "Agente 7 — NF",
            "Agente 8 — Políticas",
            "Agente 9 — Objetivo",
            "Geral — MEIrelles",
        ]
        for classificacao in classificacoes:
            resp = client.post("/feedbacks", json={"usuario_id": 1, "texto": "ok", "classificacao": classificacao})
            assert resp.status_code == 201, f"Falhou para classificacao: {classificacao}"

    def test_retorna_400_body_vazio(self, client):
        resp = client.post("/feedbacks", data="not json", content_type="application/json")

        assert resp.status_code == 400


class TestGetFeedbacks:
    def test_lista_feedbacks_do_usuario(self, client, mock_db_conn, mocker):
        lista_fake = {"feedbacks": [FEEDBACK_FAKE], "total": 1, "limit": 50, "offset": 0}
        _, conn = mock_db_conn("src.routes.feedbacks.get_db_conn")

        mocker.patch("src.routes.feedbacks.cache_get", return_value=None)
        fetch_mock = mocker.patch("src.routes.feedbacks.queries.fetch_feedbacks", return_value=lista_fake)
        cache_set_mock = mocker.patch("src.routes.feedbacks.cache_set")

        resp = client.get("/usuarios/1/feedbacks")

        assert resp.status_code == 200
        assert resp.get_json() == lista_fake
        fetch_mock.assert_called_once_with(conn, 1, 50, 0)
        cache_set_mock.assert_called_once_with("feedbacks", "1:0:50", lista_fake, Config.CACHE_TTL_FEEDBACKS)

    def test_usa_cache_quando_disponivel(self, client, mock_db_conn, mocker):
        lista_fake = {"feedbacks": [FEEDBACK_FAKE], "total": 1, "limit": 50, "offset": 0}
        mock_db_conn("src.routes.feedbacks.get_db_conn")

        mocker.patch("src.routes.feedbacks.cache_get", return_value=lista_fake)
        fetch_mock = mocker.patch("src.routes.feedbacks.queries.fetch_feedbacks")

        resp = client.get("/usuarios/1/feedbacks")

        assert resp.status_code == 200
        assert resp.get_json() == lista_fake
        fetch_mock.assert_not_called()

    def test_paginacao_com_limit_e_offset(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.feedbacks.get_db_conn")
        lista_fake = {"feedbacks": [], "total": 20, "limit": 10, "offset": 10}

        mocker.patch("src.routes.feedbacks.cache_get", return_value=None)
        fetch_mock = mocker.patch("src.routes.feedbacks.queries.fetch_feedbacks", return_value=lista_fake)
        mocker.patch("src.routes.feedbacks.cache_set")

        resp = client.get("/usuarios/1/feedbacks?limit=10&offset=10")

        assert resp.status_code == 200
        fetch_mock.assert_called_once_with(conn, 1, 10, 10)


class TestGetFeedbackById:
    def test_retorna_feedback_existente(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.feedbacks.get_db_conn")

        mocker.patch("src.routes.feedbacks.cache_get", return_value=None)
        fetch_mock = mocker.patch("src.routes.feedbacks.queries.fetch_feedback_by_id", return_value=FEEDBACK_FAKE)
        mocker.patch("src.routes.feedbacks.cache_set")

        resp = client.get("/usuarios/1/feedbacks/1")

        assert resp.status_code == 200
        assert resp.get_json() == FEEDBACK_FAKE
        fetch_mock.assert_called_once_with(conn, 1, 1)

    def test_retorna_404_quando_nao_existe(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.feedbacks.get_db_conn")

        mocker.patch("src.routes.feedbacks.cache_get", return_value=None)
        mocker.patch("src.routes.feedbacks.queries.fetch_feedback_by_id", return_value=None)

        resp = client.get("/usuarios/1/feedbacks/999")

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "not_found"


class TestPutFeedback:
    def test_atualiza_resolucao_do_feedback(self, client, mock_db_conn, mocker):
        atualizado = {**FEEDBACK_FAKE, "resolvido": True, "acao_tomada": "Lembrete ajustado"}
        _, conn = mock_db_conn("src.routes.feedbacks.get_db_conn")

        update_mock = mocker.patch("src.routes.feedbacks.queries.update_feedback", return_value=atualizado)
        invalidate_prefix_mock = mocker.patch("src.routes.feedbacks.cache_invalidate_prefix")
        mocker.patch("src.routes.feedbacks.cache_invalidate")

        payload = {"resolvido": True, "acao_tomada": "Lembrete ajustado"}
        resp = client.put("/usuarios/1/feedbacks/1", json=payload)

        assert resp.status_code == 200
        assert resp.get_json()["resolvido"] is True
        update_mock.assert_called_once_with(conn, 1, 1, payload)
        invalidate_prefix_mock.assert_called_once_with("feedbacks", "1:")

    def test_retorna_404_quando_feedback_nao_existe(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.feedbacks.get_db_conn")
        mocker.patch("src.routes.feedbacks.queries.update_feedback", return_value=None)

        resp = client.put("/usuarios/1/feedbacks/999", json={"resolvido": True})

        assert resp.status_code == 404

    def test_retorna_400_classificacao_invalida(self, client):
        resp = client.put("/usuarios/1/feedbacks/1", json={"classificacao": "invalida"})

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "invalid_classificacao"

    def test_retorna_400_body_vazio(self, client):
        resp = client.put("/usuarios/1/feedbacks/1", data="x", content_type="application/json")

        assert resp.status_code == 400


class TestGetFeedbacksResumo:
    def test_retorna_resumo_mensal(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.feedbacks.get_db_conn")

        mocker.patch("src.routes.feedbacks.cache_get", return_value=None)
        fetch_mock = mocker.patch("src.routes.feedbacks.queries.fetch_feedbacks_resumo", return_value=RESUMO_FAKE)
        mocker.patch("src.routes.feedbacks.cache_set")

        resp = client.get("/feedbacks/resumo/2026-05")

        assert resp.status_code == 200
        assert resp.get_json() == RESUMO_FAKE
        fetch_mock.assert_called_once_with(conn, "2026-05")

    def test_retorna_404_quando_resumo_nao_existe(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.feedbacks.get_db_conn")

        mocker.patch("src.routes.feedbacks.cache_get", return_value=None)
        mocker.patch("src.routes.feedbacks.queries.fetch_feedbacks_resumo", return_value=None)

        resp = client.get("/feedbacks/resumo/2026-01")

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "not_found"


class TestPostFeedbacksResumo:
    def test_cria_resumo_mensal(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.feedbacks.get_db_conn")

        insert_mock = mocker.patch("src.routes.feedbacks.queries.insert_feedbacks_resumo", return_value=RESUMO_FAKE)
        mocker.patch("src.routes.feedbacks.cache_invalidate")

        payload = {
            "mes_referencia": "2026-05",
            "total_feedbacks": 10,
            "resolvidos_na_hora": 4,
            "payload_resumo": "Resumo do mês de maio",
        }
        resp = client.post("/feedbacks/resumo", json=payload)

        assert resp.status_code == 201
        assert resp.get_json() == RESUMO_FAKE
        insert_mock.assert_called_once_with(conn, payload)

    def test_retorna_400_sem_mes_referencia(self, client):
        resp = client.post("/feedbacks/resumo", json={"total_feedbacks": 5})

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "missing_field"

    def test_retorna_400_body_vazio(self, client):
        resp = client.post("/feedbacks/resumo", data="x", content_type="application/json")

        assert resp.status_code == 400
