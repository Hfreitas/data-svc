from datetime import date, timedelta

from src.config import Config


class TestListAgendamentos:
    def test_lista_compromissos_da_semana(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamentos_fake = [
            {
                "id": 5,
                "nome_compromisso": "Reunião com cliente",
                "data_compromisso": "2026-04-21",
                "hora_compromisso": "10:00",
                "status": "confirmado",
            }
        ]
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")
        iso = date.today().isocalendar()
        semana_iso = f"{iso.year}-W{iso.week:02d}"

        mocker.patch("src.routes.agendamentos.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.agendamentos.q.list_semana", return_value=agendamentos_fake)
        cache_set_mock = mocker.patch("src.routes.agendamentos.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/agendamentos?semana=atual")

        assert resp.status_code == 200
        assert resp.get_json() == agendamentos_fake
        list_mock.assert_called_once_with(conn, usuario_id)
        cache_set_mock.assert_called_once_with(
            "agendamentos",
            f"{usuario_id}:{semana_iso}",
            agendamentos_fake,
            Config.CACHE_TTL_AGENDAMENTOS,
        )

    def test_usa_cache_na_segunda_chamada(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamentos_fake = [
            {
                "id": 5,
                "nome_compromisso": "Reunião com cliente",
                "data_compromisso": "2026-04-21",
                "hora_compromisso": "10:00",
                "status": "confirmado",
            }
        ]
        get_db_conn_mock, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        cache_get_mock = mocker.patch(
            "src.routes.agendamentos.cache_get",
            side_effect=[None, agendamentos_fake],
        )
        list_mock = mocker.patch("src.routes.agendamentos.q.list_semana", return_value=agendamentos_fake)
        mocker.patch("src.routes.agendamentos.cache_set")

        resp_1 = client.get(f"/usuarios/{usuario_id}/agendamentos?semana=atual")
        resp_2 = client.get(f"/usuarios/{usuario_id}/agendamentos?semana=atual")

        assert resp_1.status_code == 200
        assert resp_2.status_code == 200
        assert resp_1.get_json() == agendamentos_fake
        assert resp_2.get_json() == agendamentos_fake
        assert cache_get_mock.call_count == 2
        list_mock.assert_called_once_with(conn, usuario_id)
        get_db_conn_mock.assert_called_once()


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
    def test_cancela_compromisso(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamento_id = 5
        payload = {"status": "confirmado"}
        agendamento_atualizado = {
            "id": agendamento_id,
            "nome_compromisso": "Reunião com cliente",
            "status": "confirmado",
        }
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        update_mock = mocker.patch(
            "src.routes.agendamentos.q.update_status",
            return_value=agendamento_atualizado,
        )
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json=payload,
        )

        assert resp.status_code == 200
        assert resp.get_json() == agendamento_atualizado
        update_mock.assert_called_once_with(conn, agendamento_id, usuario_id, "confirmado")
        invalidate_prefix_mock.assert_called_once_with("agendamentos", f"{usuario_id}:")

    def test_retorna_404_agendamento_inexistente(self, client, mock_db_conn, mocker):
        usuario_id = 1
        agendamento_id = 999
        payload = {"status": "confirmado"}
        _, conn = mock_db_conn("src.routes.agendamentos.get_db_conn")

        update_mock = mocker.patch("src.routes.agendamentos.q.update_status", return_value=None)
        invalidate_prefix_mock = mocker.patch("src.routes.agendamentos.cache_invalidate_prefix")

        resp = client.put(
            f"/usuarios/{usuario_id}/agendamentos/{agendamento_id}",
            json=payload,
        )

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "agendamento_nao_encontrado"
        assert str(agendamento_id) in data["detail"]
        update_mock.assert_called_once_with(conn, agendamento_id, usuario_id, "confirmado")
        invalidate_prefix_mock.assert_not_called()
