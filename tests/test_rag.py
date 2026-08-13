class TestBuscaRag:
    def test_cache_hit_pula_openai_e_db(self, client, mock_db_conn, mocker):
        chunks = [{"id": 1, "content": "DAS vence dia 20", "similarity": 0.9}]
        get_db_conn_mock, _ = mock_db_conn("src.routes.rag.get_db_conn")
        mocker.patch("src.routes.rag.redis_cache.cache_get", return_value=chunks)
        client_mock = mocker.patch("src.routes.rag._get_client")

        resp = client.post("/rag/busca", json={"pergunta": "Quando vence o DAS?"})

        assert resp.status_code == 200
        assert resp.get_json()["resultados"] == chunks
        client_mock.assert_not_called()       # não gerou embedding
        get_db_conn_mock.assert_not_called()  # não bateu no Postgres

    def test_cache_miss_busca_e_grava(self, client, mock_db_conn, mocker):
        chunks = [{"id": 2, "content": "MEI", "similarity": 0.8}]
        _, conn = mock_db_conn("src.routes.rag.get_db_conn")
        mocker.patch("src.routes.rag.redis_cache.cache_get", return_value=None)
        set_mock = mocker.patch("src.routes.rag.redis_cache.cache_set")

        emb_resp = mocker.MagicMock()
        emb_resp.data = [mocker.MagicMock(embedding=[0.1, 0.2])]
        fake_client = mocker.MagicMock()
        fake_client.embeddings.create.return_value = emb_resp
        mocker.patch("src.routes.rag._get_client", return_value=fake_client)
        mocker.patch("src.routes.rag.queries.busca_semantica", return_value=chunks)

        resp = client.post("/rag/busca", json={"pergunta": "o que é MEI?"})

        assert resp.status_code == 200
        assert resp.get_json()["resultados"] == chunks
        set_mock.assert_called_once()
        assert set_mock.call_args.args[1] == chunks  # grava os chunks no cache

    def test_perfil_normalizado_e_passado_pra_query(self, client, mock_db_conn, mocker):
        chunks = [{"id": 3, "content": "Livro Caixa", "similarity": 0.8}]
        _, conn = mock_db_conn("src.routes.rag.get_db_conn")
        mocker.patch("src.routes.rag.redis_cache.cache_get", return_value=None)
        mocker.patch("src.routes.rag.redis_cache.cache_set")
        emb_resp = mocker.MagicMock()
        emb_resp.data = [mocker.MagicMock(embedding=[0.1, 0.2])]
        fake = mocker.MagicMock()
        fake.embeddings.create.return_value = emb_resp
        mocker.patch("src.routes.rag._get_client", return_value=fake)
        busca = mocker.patch("src.routes.rag.queries.busca_semantica", return_value=chunks)

        resp = client.post("/rag/busca", json={"pergunta": "carnê-leão?", "perfil": "profissional_liberal"})

        assert resp.status_code == 200
        # profissional_liberal -> 'pl' passado como 5º arg pra busca_semantica
        assert busca.call_args.args[4] == "pl"

    def test_perfil_invalido_vira_none(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.rag.get_db_conn")
        mocker.patch("src.routes.rag.redis_cache.cache_get", return_value=None)
        mocker.patch("src.routes.rag.redis_cache.cache_set")
        emb_resp = mocker.MagicMock()
        emb_resp.data = [mocker.MagicMock(embedding=[0.1])]
        fake = mocker.MagicMock()
        fake.embeddings.create.return_value = emb_resp
        mocker.patch("src.routes.rag._get_client", return_value=fake)
        busca = mocker.patch("src.routes.rag.queries.busca_semantica", return_value=[])

        resp = client.post("/rag/busca", json={"pergunta": "x", "perfil": "xpto"})

        assert resp.status_code == 200
        assert busca.call_args.args[4] is None  # perfil inválido = sem filtro

    def test_perfil_muda_cache_key(self, client, mock_db_conn, mocker):
        """Mesma pergunta com perfis diferentes NÃO compartilha cache."""
        mock_db_conn("src.routes.rag.get_db_conn")
        get = mocker.patch("src.routes.rag.redis_cache.cache_get", return_value=None)
        mocker.patch("src.routes.rag.redis_cache.cache_set")
        emb_resp = mocker.MagicMock()
        emb_resp.data = [mocker.MagicMock(embedding=[0.1])]
        fake = mocker.MagicMock()
        fake.embeddings.create.return_value = emb_resp
        mocker.patch("src.routes.rag._get_client", return_value=fake)
        mocker.patch("src.routes.rag.queries.busca_semantica", return_value=[])

        client.post("/rag/busca", json={"pergunta": "DAS?", "perfil": "mei"})
        client.post("/rag/busca", json={"pergunta": "DAS?", "perfil": "pl"})
        k_mei = get.call_args_list[0].args[0]
        k_pl = get.call_args_list[1].args[0]
        assert k_mei != k_pl

    def test_missing_field(self, client):
        resp = client.post("/rag/busca", json={})
        assert resp.status_code == 400
