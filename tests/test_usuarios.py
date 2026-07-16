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

    def test_retorna_campos_onboarding_no_perfil(self, client, mock_db_conn, mocker):
        telefone = "5511999999999"
        usuario_fake = {
            "id": 1,
            "numero_telefone": telefone,
            "nome": "Fulano",
            "estado_atual": "menu",
            "cluster": "comida",
            "onboarding_step": "NEGOCIO",
            "confirmacao_lembretes": True,
            "onboarding_concluido": False,
        }
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")
        mocker.patch("src.routes.usuarios.cache_get", return_value=None)
        mocker.patch("src.routes.usuarios.q.find_by_telefone", return_value=usuario_fake)
        mocker.patch("src.routes.usuarios.cache_set")

        resp = client.get(f"/usuarios?telefone={telefone}")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["cluster"] == "comida"
        assert data["onboarding_step"] == "NEGOCIO"
        assert data["confirmacao_lembretes"] is True
        assert data["onboarding_concluido"] is False

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

    def test_atualiza_cluster_e_onboarding_step(self, client, mock_db_conn, mocker):
        usuario_id = 1
        usuario_fake = {
            "id": usuario_id,
            "numero_telefone": "5511999999999",
            "nome": "Fulano",
            "cluster": "comida",
            "onboarding_step": "NEGOCIO",
            "onboarding_concluido": False,
            "confirmacao_lembretes": True,
        }
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")
        update_mock = mocker.patch("src.routes.usuarios.q.update", return_value=usuario_fake)
        mocker.patch("src.routes.usuarios.cache_invalidate")

        payload = {
            "cluster": "comida",
            "onboarding_step": "NEGOCIO",
            "confirmacao_lembretes": True,
            "onboarding_concluido": False,
        }
        resp = client.put(f"/usuarios/{usuario_id}", json=payload)

        assert resp.status_code == 200
        call_fields = update_mock.call_args.args[2]
        assert call_fields.get("cluster") == "comida"
        assert call_fields.get("onboarding_step") == "NEGOCIO"
        assert call_fields.get("confirmacao_lembretes") is True
        assert call_fields.get("onboarding_concluido") is False


class TestResetarDemo:
    def test_reseta_usuario_e_invalida_cache(self, client, mock_db_conn, mocker):
        usuario_id = 7
        usuario_resetado = {
            "id": usuario_id,
            "numero_telefone": "5511977776666",
            "estado_atual": "menu",
            "interacao_previa": False,
            "onboarding_step": None,
            "onboarding_concluido": False,
        }
        _, conn = mock_db_conn("src.routes.usuarios.get_db_conn")

        reset_mock = mocker.patch(
            "src.routes.usuarios.q.reset_demo", return_value=usuario_resetado
        )
        cache_invalidate_mock = mocker.patch("src.routes.usuarios.cache_invalidate")

        resp = client.post(f"/usuarios/{usuario_id}/resetar-demo")

        assert resp.status_code == 200
        assert resp.get_json() == usuario_resetado
        reset_mock.assert_called_once_with(conn, usuario_id)
        assert cache_invalidate_mock.call_count == 2
        cache_invalidate_mock.assert_any_call("usuario", usuario_resetado["numero_telefone"])
        cache_invalidate_mock.assert_any_call("usuario", f"id:{usuario_id}")

    def test_retorna_404_usuario_inexistente(self, client, mock_db_conn, mocker):
        usuario_id = 999
        mock_db_conn("src.routes.usuarios.get_db_conn")

        mocker.patch("src.routes.usuarios.q.reset_demo", return_value=None)
        cache_invalidate_mock = mocker.patch("src.routes.usuarios.cache_invalidate")

        resp = client.post(f"/usuarios/{usuario_id}/resetar-demo")

        assert resp.status_code == 404
        assert resp.get_json() == {"error": "usuario_nao_encontrado"}
        cache_invalidate_mock.assert_not_called()


class TestResetDemoQuery:
    """Testa src.queries.usuarios.reset_demo direto (sem mockar a função),
    pra travar o escopo: só feedbacks/chat_memory são apagados, dado de
    negócio (agenda, comprovantes, lista de compras) fica intacto."""

    def test_apaga_so_feedbacks_e_chat_memory(self, mocker):
        import src.queries.usuarios as q

        usuario_id = 42
        usuario_row = {"id": usuario_id, "numero_telefone": "5511977776666", "estado_atual": "menu"}

        executed_sql = []

        cursor = mocker.MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchone.return_value = usuario_row

        def _execute(sql, params=None):
            executed_sql.append(" ".join(sql.split()))

        cursor.execute.side_effect = _execute

        conn = mocker.MagicMock()
        conn.cursor.return_value = cursor

        result = q.reset_demo(conn, usuario_id)

        assert result == usuario_row

        delete_statements = [sql for sql in executed_sql if sql.startswith("DELETE")]
        assert len(delete_statements) == 2
        assert any("public.feedbacks" in sql for sql in delete_statements)
        assert any("public.chat_memory" in sql for sql in delete_statements)

        tabelas_de_negocio = [
            "public.comprovantes",
            "public.agendamentos",
            "public.contas_recorrentes",
            "public.lista_compras",
            "public.itens_lista",
            "public.google_calendar_events",
            "public.agendamento_estado",
            "public.agendamento_auditoria",
            "public.lembrete_contas_log",
        ]
        for tabela in tabelas_de_negocio:
            assert not any(tabela in sql for sql in executed_sql), f"{tabela} não deveria ser apagada"

    def test_retorna_none_se_usuario_nao_existe(self, mocker):
        import src.queries.usuarios as q

        cursor = mocker.MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchone.return_value = None

        conn = mocker.MagicMock()
        conn.cursor.return_value = cursor

        result = q.reset_demo(conn, 999)

        assert result is None
        cursor.execute.assert_called_once()
