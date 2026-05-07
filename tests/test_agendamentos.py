from datetime import date, timedelta

from src.config import Config


class TestListAgendamentos:
    def test_lista_compromissos_futuros_com_scope_future(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_futura = (date.today() + timedelta(days=9)).isoformat()
        agendamentos_fake = [
            {
                "id": 9,
                "nome_compromisso": "Follow-up comercial",
                "data_compromisso": data_futura,
                "hora_compromisso": "15:30",
                "status": "agendado",
            }
        ]
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        cache_get_mock = mocker.patch("src.routes.agendamentos.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.agendamentos.q.list_agendamentos", return_value=agendamentos_fake)
        cache_set_mock = mocker.patch("src.routes.agendamentos.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/agendamentos?scope=future")

        assert resp.status_code == 200
        assert resp.get_json() == agendamentos_fake
        cache_get_mock.assert_called_once_with("agendamentos", f"{usuario_id}:future")
        list_mock.assert_called_once_with(conn, usuario_id)
        cache_set_mock.assert_called_once_with(
            "agendamentos",
            f"{usuario_id}:future",
            agendamentos_fake,
            Config.CACHE_TTL_AGENDAMENTOS,
        )

    def test_usa_cache_na_segunda_chamada(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_futura = (date.today() + timedelta(days=9)).isoformat()
        agendamentos_fake = [
            {
                "id": 9,
                "nome_compromisso": "Follow-up comercial",
                "data_compromisso": data_futura,
                "hora_compromisso": "15:30",
                "status": "agendado",
            }
        ]
        get_db_conn_mock, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        cache_get_mock = mocker.patch(
            "src.routes.agendamentos.cache_get",
            side_effect=[None, agendamentos_fake],
        )
        list_mock = mocker.patch("src.routes.agendamentos.q.list_agendamentos", return_value=agendamentos_fake)
        mocker.patch("src.routes.agendamentos.cache_set")

        resp_1 = client.get(f"/usuarios/{usuario_id}/agendamentos?scope=future")
        resp_2 = client.get(f"/usuarios/{usuario_id}/agendamentos?scope=future")

        assert resp_1.status_code == 200
        assert resp_2.status_code == 200
        assert resp_1.get_json() == agendamentos_fake
        assert resp_2.get_json() == agendamentos_fake
        assert cache_get_mock.call_count == 2
        list_mock.assert_called_once_with(conn, usuario_id)
        get_db_conn_mock.assert_called_once()

    def test_retorna_400_sem_scope(self, client):
        resp = client.get("/usuarios/1/agendamentos")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "parâmetro 'scope' inválido" in data["detail"]

    def test_retorna_400_para_scope_invalido(self, client):
        resp = client.get("/usuarios/1/agendamentos?scope=week")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "parâmetro 'scope' inválido" in data["detail"]


class TestCreateAgendamento:
    def test_cria_compromisso(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_futura = (date.today() + timedelta(days=2)).isoformat()
        payload = {
            "nome_compromisso": "Call de fechamento",
            "data_compromisso": data_futura,
            "hora_compromisso": "23:59",
        }
        agendamento_fake = {
            "id": 20,
            "nome_compromisso": payload["nome_compromisso"],
            "data_compromisso": data_futura,
            "hora_compromisso": "23:59",
            "status": "confirmado",
        }
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        create_mock = mocker.patch("src.routes.agendamentos.q.create", return_value=agendamento_fake)
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.post(f"/usuarios/{usuario_id}/agendamentos", json=payload)

        assert resp.status_code == 201
        assert resp.get_json() == agendamento_fake
        create_mock.assert_called_once_with(conn, usuario_id, payload)
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")

    def test_retorna_400_sem_campos_obrigatorios(self, client):
        resp = client.post("/usuarios/1/agendamentos", json={})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "campos obrigatórios ausentes" in data["detail"]

    def test_invalida_cache_apos_criacao(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_futura = (date.today() + timedelta(days=2)).isoformat()
        payload = {
            "nome_compromisso": "Revisão de proposta",
            "data_compromisso": data_futura,
            "hora_compromisso": "23:59",
        }

        mock_db_conn("src.routes.agendamentos.get_db_conn")
        mocker.patch("src.routes.agendamentos.q.create", return_value={"id": 21, "status": "confirmado"})
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.post(f"/usuarios/{usuario_id}/agendamentos", json=payload)

        assert resp.status_code == 201
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")


class TestUpdateAgendamento:
    def test_atualiza_status_apenas(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamento_id = 5
        payload = {"status": "cancelado"}
        agendamento_atualizado = {
            "id": agendamento_id,
            "nome_compromisso": "Reunião com cliente",
            "data_compromisso": "2026-05-10",
            "hora_compromisso": "15:00",
            "status": "cancelado",
        }
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        update_mock = mocker.patch(
            "src.routes.agendamentos.q.update",
            return_value=agendamento_atualizado,
        )
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json=payload,
        )

        assert resp.status_code == 200
        assert resp.get_json() == agendamento_atualizado
        update_mock.assert_called_once_with(conn, agendamento_id, usuario_id, {"status": "cancelado"})
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")

    def test_atualiza_nome_compromisso_apenas(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamento_id = 5
        payload = {"nome_compromisso": "Novo nome do compromisso"}
        agendamento_atualizado = {
            "id": agendamento_id,
            "nome_compromisso": "Novo nome do compromisso",
            "data_compromisso": "2026-05-10",
            "hora_compromisso": "15:00",
            "status": "confirmado",
        }
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        update_mock = mocker.patch(
            "src.routes.agendamentos.q.update",
            return_value=agendamento_atualizado,
        )
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json=payload,
        )

        assert resp.status_code == 200
        assert resp.get_json() == agendamento_atualizado
        update_mock.assert_called_once_with(conn, agendamento_id, usuario_id, {"nome_compromisso": "Novo nome do compromisso"})
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")

    def test_atualiza_multiplos_campos(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamento_id = 5
        data_futura = (date.today() + timedelta(days=5)).isoformat()
        payload = {
            "nome_compromisso": "Novo compromisso",
            "data_compromisso": data_futura,
            "hora_compromisso": "10:30",
            "status": "agendado",
        }
        agendamento_atualizado = {
            "id": agendamento_id,
            "nome_compromisso": "Novo compromisso",
            "data_compromisso": data_futura,
            "hora_compromisso": "10:30",
            "status": "agendado",
        }
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        update_mock = mocker.patch(
            "src.routes.agendamentos.q.update",
            return_value=agendamento_atualizado,
        )
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json=payload,
        )

        assert resp.status_code == 200
        assert resp.get_json() == agendamento_atualizado
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")

    def test_retorna_404_agendamento_inexistente(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamento_id = 999
        payload = {"status": "confirmado"}
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        update_mock = mocker.patch("src.routes.agendamentos.q.update", return_value=None)
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json=payload,
        )

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "agendamento_nao_encontrado"
        assert str(agendamento_id) in data["detail"]
        invalidate_prefix_mock.assert_not_called()

    def test_retorna_400_body_vazio(self, client):
        usuario_id = 1
        agendamento_id = 5

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json={},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "body" in data["detail"].lower() or "campo" in data["detail"].lower()

    def test_retorna_400_status_invalido(self, client):
        usuario_id = 1
        agendamento_id = 5

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json={"status": "invalido"},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "status" in data["detail"].lower()

    def test_retorna_400_data_no_passado(self, client):
        usuario_id = 1
        agendamento_id = 5
        data_passada = (date.today() - timedelta(days=1)).isoformat()

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json={"data_compromisso": data_passada},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "passado" in data["detail"].lower()

    def test_retorna_400_hora_invalida(self, client):
        usuario_id = 1
        agendamento_id = 5

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json={"hora_compromisso": "25:00"},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "hora_compromisso" in data["detail"].lower()


class TestCancelAllAgendamentos:
    def test_cancela_todos_agendamentos_ativos(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_futura = (date.today() + timedelta(days=5)).isoformat()
        agendamentos_cancelados = [
            {
                "nome_compromisso": "Reunião com gerente",
                "data_compromisso": data_futura,
                "hora_compromisso": "10:00",
            },
            {
                "nome_compromisso": "Ligação de acompanhamento",
                "data_compromisso": data_futura,
                "hora_compromisso": "14:30",
            },
        ]
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        cancel_all_mock = mocker.patch(
            "src.routes.agendamentos.q.cancel_all",
            return_value=agendamentos_cancelados,
        )
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.delete(f"/usuarios/{usuario_id}/agendamentos")

        assert resp.status_code == 200
        assert resp.get_json() == agendamentos_cancelados
        cancel_all_mock.assert_called_once_with(conn, usuario_id)
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")

    def test_retorna_lista_vazia_sem_agendamentos_ativos(self, client, mock_db_conn, mocker):
        usuario_id = 1
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        cancel_all_mock = mocker.patch(
            "src.routes.agendamentos.q.cancel_all",
            return_value=[],
        )
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.delete(f"/usuarios/{usuario_id}/agendamentos")

        assert resp.status_code == 200
        assert resp.get_json() == []
        cancel_all_mock.assert_called_once_with(conn, usuario_id)
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")

    def test_invalida_cache_apos_cancelamento_em_massa(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamentos_cancelados = [
            {
                "nome_compromisso": "Compromisso 1",
                "data_compromisso": (date.today() + timedelta(days=3)).isoformat(),
                "hora_compromisso": "09:00",
            },
        ]
        mock_db_conn("src.routes.agendamentos.get_db_conn")
        mocker.patch("src.routes.agendamentos.q.cancel_all", return_value=agendamentos_cancelados)
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.delete(f"/usuarios/{usuario_id}/agendamentos")

        assert resp.status_code == 200
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")
