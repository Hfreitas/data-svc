from datetime import date, datetime, timezone

PERFIL_FAKE = {
    "id": 1,
    "nome": "João",
    "razao_social": "Pizzaria do João",
    "tipo_negocio": "produto",
    "descricao_negocio": "Faço pizzas artesanais",
    "descricao_objetivo": "Abrir segunda unidade",
    "data_primeiro_contato": datetime(2026, 4, 20, tzinfo=timezone.utc),
    "ultimo_relatorio": None,
    "confirmacao_lembretes": False,
    "interacao_previa": True,
    "descricao_completa": True,
    "proximo_campo_fila": "confirmacao_lembretes",
    "status_trial": "trial",
}

SEMANA_FAKE = {"contagem": 3, "total_vendas": 200.0, "total_gastos": 80.0, "saldo": 120.0}
MES_FAKE = {"contagem": 10, "total_vendas": 800.0, "total_gastos": 300.0, "saldo": 500.0}
HISTORICO_FAKE = [
    {"ano": 2026, "mes": 3, "total_vendas": 750.0, "total_gastos": 280.0},
    {"ano": 2026, "mes": 4, "total_vendas": 820.0, "total_gastos": 310.0},
]
GASTOS_REC_FAKE = [{"item": "aluguel", "meses_consecutivos": 3, "valor": 800.0}]
LOG_FAKE = {"id": 42, "request_id": "abc-123", "created_at": "2026-05-20T10:00:00"}


class TestGetContextoBusiness:
    def test_retorna_contexto_completo(self, client, mock_db_conn, mocker):
        mocker.patch("src.routes.business.cache_get", return_value=None)
        mocker.patch("src.routes.business.cache_set")
        _, conn = mock_db_conn("src.routes.business.get_db_conn")
        mocker.patch("src.routes.business.q.get_contexto_usuario", return_value=PERFIL_FAKE)
        mocker.patch("src.routes.business.q.get_registros_semana", return_value=SEMANA_FAKE)
        mocker.patch("src.routes.business.q.get_registros_mes", return_value=MES_FAKE)
        mocker.patch("src.routes.business.q.get_historico_meses", return_value=HISTORICO_FAKE)
        mocker.patch("src.routes.business.q.get_faturamento_acumulado_ano", return_value=1620.0)
        mocker.patch("src.routes.business.q.get_gastos_recorrentes", return_value=GASTOS_REC_FAKE)

        resp = client.get("/usuarios/1/contexto-business")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["perfil"]["nome_mei"] == "João"
        assert data["perfil"]["nome_negocio"] == "Pizzaria do João"
        assert data["perfil"]["cluster"] == "produto"
        assert data["perfil"]["descricao_completa"] is True
        assert data["flags"]["primeiro_relatorio"] is True
        assert data["flags"]["status_trial"] == "trial"
        assert data["flags"]["confirmacao_lembretes"] is False
        assert data["flags"]["proximo_campo_fila"] == "confirmacao_lembretes"
        assert data["flags"]["mes_uso"] >= 1
        assert data["data_context"]["dia_semana"] != ""
        assert data["data_context"]["semana_do_mes"] >= 1
        assert data["financeiro"]["registros_semana"] == SEMANA_FAKE
        assert data["financeiro"]["registros_mes"] == MES_FAKE
        assert data["financeiro"]["historico_meses"] == HISTORICO_FAKE
        assert data["financeiro"]["faturamento_acumulado_ano"] == 1620.0
        assert data["financeiro"]["gastos_recorrentes"] == GASTOS_REC_FAKE
        assert data["financeiro"]["ultimo_relatorio"] is None

    def test_retorna_cache_quando_disponivel(self, client, mocker):
        cached_payload = {"perfil": {"nome_mei": "Cached"}}
        mocker.patch("src.routes.business.cache_get", return_value=cached_payload)
        cache_set_mock = mocker.patch("src.routes.business.cache_set")

        resp = client.get("/usuarios/1/contexto-business")

        assert resp.status_code == 200
        assert resp.get_json() == cached_payload
        cache_set_mock.assert_not_called()

    def test_retorna_404_usuario_inexistente(self, client, mock_db_conn, mocker):
        mocker.patch("src.routes.business.cache_get", return_value=None)
        mock_db_conn("src.routes.business.get_db_conn")
        mocker.patch("src.routes.business.q.get_contexto_usuario", return_value=None)

        resp = client.get("/usuarios/999/contexto-business")

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "usuario_nao_encontrado"

    def test_primeiro_relatorio_false_quando_tem_ultimo_relatorio(self, client, mock_db_conn, mocker):
        mocker.patch("src.routes.business.cache_get", return_value=None)
        mocker.patch("src.routes.business.cache_set")
        mock_db_conn("src.routes.business.get_db_conn")
        perfil = {**PERFIL_FAKE, "ultimo_relatorio": date(2026, 5, 1)}
        mocker.patch("src.routes.business.q.get_contexto_usuario", return_value=perfil)
        mocker.patch("src.routes.business.q.get_registros_semana", return_value=SEMANA_FAKE)
        mocker.patch("src.routes.business.q.get_registros_mes", return_value=MES_FAKE)
        mocker.patch("src.routes.business.q.get_historico_meses", return_value=[])
        mocker.patch("src.routes.business.q.get_faturamento_acumulado_ano", return_value=0.0)
        mocker.patch("src.routes.business.q.get_gastos_recorrentes", return_value=[])

        resp = client.get("/usuarios/1/contexto-business")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["flags"]["primeiro_relatorio"] is False
        assert data["financeiro"]["ultimo_relatorio"] == "2026-05-01"

    def test_mes_uso_calculado_corretamente(self, client, mock_db_conn, mocker):
        mocker.patch("src.routes.business.cache_get", return_value=None)
        mocker.patch("src.routes.business.cache_set")
        mock_db_conn("src.routes.business.get_db_conn")
        # Usuário criado 2 meses atrás → mes_uso deve ser 3 (mês atual incluído)
        hoje = date.today()
        dois_meses_atras = datetime(hoje.year, hoje.month - 2 if hoje.month > 2 else hoje.month + 10, 1, tzinfo=timezone.utc)
        perfil = {**PERFIL_FAKE, "data_primeiro_contato": dois_meses_atras}
        mocker.patch("src.routes.business.q.get_contexto_usuario", return_value=perfil)
        mocker.patch("src.routes.business.q.get_registros_semana", return_value=SEMANA_FAKE)
        mocker.patch("src.routes.business.q.get_registros_mes", return_value=MES_FAKE)
        mocker.patch("src.routes.business.q.get_historico_meses", return_value=[])
        mocker.patch("src.routes.business.q.get_faturamento_acumulado_ano", return_value=0.0)
        mocker.patch("src.routes.business.q.get_gastos_recorrentes", return_value=[])

        resp = client.get("/usuarios/1/contexto-business")

        assert resp.status_code == 200
        assert resp.get_json()["flags"]["mes_uso"] == 3

    def test_usuario_sem_data_primeiro_contato(self, client, mock_db_conn, mocker):
        mocker.patch("src.routes.business.cache_get", return_value=None)
        mocker.patch("src.routes.business.cache_set")
        mock_db_conn("src.routes.business.get_db_conn")
        perfil = {**PERFIL_FAKE, "data_primeiro_contato": None}
        mocker.patch("src.routes.business.q.get_contexto_usuario", return_value=perfil)
        mocker.patch("src.routes.business.q.get_registros_semana", return_value=SEMANA_FAKE)
        mocker.patch("src.routes.business.q.get_registros_mes", return_value=MES_FAKE)
        mocker.patch("src.routes.business.q.get_historico_meses", return_value=[])
        mocker.patch("src.routes.business.q.get_faturamento_acumulado_ano", return_value=0.0)
        mocker.patch("src.routes.business.q.get_gastos_recorrentes", return_value=[])

        resp = client.get("/usuarios/1/contexto-business")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["flags"]["mes_uso"] == 0
        assert data["data_context"]["data_inicio_meirelles"] is None


class TestPostMeicheckLog:
    def test_insere_log_com_payload_completo(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.business.get_db_conn")
        insert_mock = mocker.patch("src.routes.business.q.insert_meicheck_log", return_value=LOG_FAKE)

        payload = {
            "request_id": "abc-123",
            "trigger_type": "webhook",
            "integrity_score": 85,
            "can_proceed": True,
            "cluster_category": "produto",
        }
        resp = client.post("/usuarios/1/meicheck-logs", json=payload)

        assert resp.status_code == 201
        assert resp.get_json()["id"] == 42
        insert_mock.assert_called_once()
        call_args = insert_mock.call_args[0]
        assert call_args[0] is conn
        assert call_args[1]["usuario_id"] == "1"

    def test_usa_usuario_id_do_body_se_presente(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.business.get_db_conn")
        insert_mock = mocker.patch("src.routes.business.q.insert_meicheck_log", return_value=LOG_FAKE)

        payload = {"request_id": "xyz", "usuario_id": "55119999"}
        client.post("/usuarios/1/meicheck-logs", json=payload)

        call_data = insert_mock.call_args[0][1]
        assert call_data["usuario_id"] == "55119999"

    def test_retorna_400_sem_body_json(self, client):
        resp = client.post("/usuarios/1/meicheck-logs", data="not-json", content_type="text/plain")

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "body_invalido"

    def test_retorna_400_body_nao_objeto(self, client):
        resp = client.post("/usuarios/1/meicheck-logs", json=[1, 2, 3])

        assert resp.status_code == 400
