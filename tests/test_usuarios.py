from src.config import Config


class TestGetUsuario:
    def test_retorna_usuario_existente(self, client, mock_db_conn, mocker):
        telefone = "5511999999999"
        usuario_fake = {
            "id": 1,
            "numero_telefone": telefone,
            "nome": "Fulano",
            "razao_social": "Fulano ME",
            "estado_atual": "menu",
        }
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")

        mocker.patch("src.routes.usuarios.cache_get", return_value=None)
        find_mock = mocker.patch("src.routes.usuarios.q.find_by_telefone", return_value=usuario_fake)
        cache_set_mock = mocker.patch("src.routes.usuarios.cache_set")

        resp = client.get(f"/usuarios?telefone={telefone}")

        assert resp.status_code == 200
        assert resp.get_json() == usuario_fake
        find_mock.assert_called_once_with(conn, telefone)
        cache_set_mock.assert_called_once_with(
            "usuario",
            telefone,
            usuario_fake,
            Config.CACHE_TTL_USUARIO,
        )

    def test_retorna_404_quando_nao_encontrado(self, client, mock_db_conn, mocker):
        telefone = "5511999999999"
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")

        mocker.patch("src.routes.usuarios.cache_get", return_value=None)
        find_mock = mocker.patch("src.routes.usuarios.q.find_by_telefone", return_value=None)

        resp = client.get(f"/usuarios?telefone={telefone}")

        assert resp.status_code == 404
        assert resp.get_json() == {"error": "usuario_nao_encontrado"}
        find_mock.assert_called_once_with(conn, telefone)

    def test_retorna_400_sem_telefone(self, client):
        resp = client.get("/usuarios")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "parâmetro 'telefone' inválido" in data["detail"]

    def test_usa_cache_no_segundo_request(self, client, mock_db_conn, mocker):
        telefone = "5511999999999"
        usuario_fake = {
            "id": 1,
            "numero_telefone": telefone,
            "nome": "Fulano",
        }
        get_db_conn_mock, conn = mock_db_conn("src.routes.usuarios.get_db_conn")

        cache_get_mock = mocker.patch(
            "src.routes.usuarios.cache_get",
            side_effect=[None, usuario_fake],
        )
        find_mock = mocker.patch(
            "src.routes.usuarios.q.find_by_telefone",
            return_value=usuario_fake,
        )
        mocker.patch("src.routes.usuarios.cache_set")

        resp_1 = client.get(f"/usuarios?telefone={telefone}")
        resp_2 = client.get(f"/usuarios?telefone={telefone}")

        assert resp_1.status_code == 200
        assert resp_2.status_code == 200
        assert resp_1.get_json() == usuario_fake
        assert resp_2.get_json() == usuario_fake

        assert cache_get_mock.call_count == 2
        find_mock.assert_called_once_with(conn, telefone)
        get_db_conn_mock.assert_called_once()


class TestCreateUsuario:
    def test_cria_novo_usuario(self, client, mock_db_conn, mocker):
        payload = {
            "numero_telefone": "5511988887777",
            "nome": "Maria",
            "razao_social": "Maria Doces",
        }
        usuario_criado = {
            "id": 10,
            "numero_telefone": payload["numero_telefone"],
            "nome": payload["nome"],
            "razao_social": payload["razao_social"],
        }
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")

        upsert_mock = mocker.patch("src.routes.usuarios.q.upsert", return_value=usuario_criado)
        cache_invalidate_mock = mocker.patch("src.routes.usuarios.cache_invalidate")

        resp = client.post("/usuarios", json=payload)

        assert resp.status_code == 200
        assert resp.get_json() == usuario_criado
        upsert_mock.assert_called_once_with(
            conn,
            payload["numero_telefone"],
            payload["nome"],
            payload["razao_social"],
        )
        cache_invalidate_mock.assert_called_once_with("usuario", payload["numero_telefone"])

    def test_retorna_existente_se_telefone_ja_cadastrado(self, client, mock_db_conn, mocker):
        payload = {
            "numero_telefone": "5511988887777",
            "nome": "Outro Nome",
            "razao_social": "Outra Razao",
        }
        usuario_existente = {
            "id": 10,
            "numero_telefone": payload["numero_telefone"],
            "nome": "Maria",
            "razao_social": "Maria Doces",
        }
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")

        upsert_mock = mocker.patch("src.routes.usuarios.q.upsert", return_value=usuario_existente)

        resp = client.post("/usuarios", json=payload)

        assert resp.status_code == 200
        assert resp.get_json()["id"] == usuario_existente["id"]
        assert resp.get_json()["numero_telefone"] == payload["numero_telefone"]
        upsert_mock.assert_called_once_with(
            conn,
            payload["numero_telefone"],
            payload["nome"],
            payload["razao_social"],
        )

    def test_retorna_400_sem_campos_obrigatorios(self, client):
        resp = client.post("/usuarios", json={})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "campos obrigatórios ausentes: numero_telefone" in data["detail"]


class TestUpdateUsuario:
    def test_atualiza_estado_atual(self, client, mock_db_conn, mocker):
        usuario_id = 5
        payload = {"estado_atual": "menu"}
        usuario_atualizado = {
            "id": usuario_id,
            "numero_telefone": "5511912345678",
            "estado_atual": "menu",
        }
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")

        update_mock = mocker.patch("src.routes.usuarios.q.update", return_value=usuario_atualizado)
        cache_invalidate_mock = mocker.patch("src.routes.usuarios.cache_invalidate")

        resp = client.put(f"/usuarios/{usuario_id}", json=payload)

        assert resp.status_code == 200
        assert resp.get_json() == usuario_atualizado
        update_mock.assert_called_once_with(conn, usuario_id, payload)
        assert cache_invalidate_mock.call_count == 2
        cache_invalidate_mock.assert_any_call("usuario", usuario_atualizado["numero_telefone"])
        cache_invalidate_mock.assert_any_call("usuario", f"id:{usuario_id}")

    def test_retorna_404_usuario_inexistente(self, client, mock_db_conn, mocker):
        usuario_id = 999
        payload = {"estado_atual": "menu"}

        mock_db_conn("src.routes.usuarios.get_db_conn")

        mocker.patch("src.routes.usuarios.q.update", return_value=None)
        cache_invalidate_mock = mocker.patch("src.routes.usuarios.cache_invalidate")

        resp = client.put(f"/usuarios/{usuario_id}", json=payload)

        assert resp.status_code == 404
        assert resp.get_json() == {"error": "usuario_nao_encontrado"}
        cache_invalidate_mock.assert_not_called()

    def test_invalida_cache_apos_update(self, client, mock_db_conn, mocker):
        usuario_id = 42
        payload = {"nome": "Nome Atualizado"}
        usuario_atualizado = {
            "id": usuario_id,
            "numero_telefone": "5511990000000",
            "nome": "Nome Atualizado",
        }

        mock_db_conn("src.routes.usuarios.get_db_conn")

        mocker.patch("src.routes.usuarios.q.update", return_value=usuario_atualizado)
        cache_invalidate_mock = mocker.patch("src.routes.usuarios.cache_invalidate")

        resp = client.put(f"/usuarios/{usuario_id}", json=payload)

        assert resp.status_code == 200
        assert cache_invalidate_mock.call_count == 2
        cache_invalidate_mock.assert_any_call("usuario", usuario_atualizado["numero_telefone"])
        cache_invalidate_mock.assert_any_call("usuario", f"id:{usuario_id}")
