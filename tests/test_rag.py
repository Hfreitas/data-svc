from src import vector
from src.config import Config


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


class TestBackendUpstash:
    """Dual-path atrás de RAG_BACKEND (F4 do plano Upstash).

    O pgvector é o default e continua sendo o caminho de fallback: qualquer falha
    do índice novo tem que degradar para ele, nunca para 200 vazio.
    """

    @staticmethod
    def _preparar(mocker, backend="upstash"):
        mocker.patch.object(Config, "RAG_BACKEND", backend)
        mocker.patch("src.routes.rag.redis_cache.cache_get", return_value=None)
        mocker.patch("src.routes.rag.redis_cache.cache_set")
        emb = mocker.MagicMock()
        emb.data = [mocker.MagicMock(embedding=[0.1])]
        fake = mocker.MagicMock()
        fake.embeddings.create.return_value = emb
        mocker.patch("src.routes.rag._get_client", return_value=fake)

    def test_flag_upstash_usa_o_indice_e_nao_o_postgres(self, client, mock_db_conn, mocker):
        self._preparar(mocker)
        db, _ = mock_db_conn("src.routes.rag.get_db_conn")
        pg = mocker.patch("src.routes.rag.queries.busca_semantica", return_value=[])
        up = mocker.patch("src.routes.rag.vector.busca_semantica", return_value=[
            {"id": 1, "content": "x", "similarity": 0.5}
        ])

        resp = client.post("/rag/busca", json={"pergunta": "DAS?", "perfil": "mei"})

        assert resp.status_code == 200
        up.assert_called_once()
        pg.assert_not_called()
        db.assert_not_called()  # nem abre conexão com o Postgres

    def test_default_continua_pgvector(self, client, mock_db_conn, mocker):
        # flag ausente/errada não pode desviar tráfego para o índice novo
        self._preparar(mocker, backend="pgvector")
        mock_db_conn("src.routes.rag.get_db_conn")
        pg = mocker.patch("src.routes.rag.queries.busca_semantica", return_value=[])
        up = mocker.patch("src.routes.rag.vector.busca_semantica")

        client.post("/rag/busca", json={"pergunta": "DAS?", "perfil": "mei"})

        pg.assert_called_once()
        up.assert_not_called()

    def test_upstash_fora_do_ar_cai_no_pgvector_e_loga(self, client, mock_db_conn, mocker, capsys):
        # fallback mudo faria a Upstash parecer saudável enquanto o pgvector
        # serve 100% do tráfego — o log é o que separa degradação de ilusão
        self._preparar(mocker)
        mock_db_conn("src.routes.rag.get_db_conn")
        chunks = [{"id": 9, "content": "do postgres", "similarity": 0.7}]
        pg = mocker.patch("src.routes.rag.queries.busca_semantica", return_value=chunks)
        mocker.patch(
            "src.routes.rag.vector.busca_semantica",
            side_effect=vector.VectorIndisponivel("HTTPError: 500"),
        )

        resp = client.post("/rag/busca", json={"pergunta": "DAS?", "perfil": "mei"})

        assert resp.status_code == 200
        assert resp.get_json()["resultados"] == chunks
        pg.assert_called_once()
        assert "[rag]" in capsys.readouterr().out

    def test_sem_perfil_cai_no_pgvector(self, client, mock_db_conn, mocker):
        # não existe namespace "tudo" na Upstash: o default tem zero vetores.
        # `vector` recusa levantando, e a rota tem que degradar, não devolver [].
        self._preparar(mocker)
        mock_db_conn("src.routes.rag.get_db_conn")
        pg = mocker.patch("src.routes.rag.queries.busca_semantica", return_value=[])

        resp = client.post("/rag/busca", json={"pergunta": "DAS?"})

        assert resp.status_code == 200
        pg.assert_called_once()

    def test_backend_entra_na_cache_key(self, client, mock_db_conn, mocker):
        # o L2 (TTL 3600s) não sabe qual backend gerou a linha. Sem o backend na
        # chave, virar a flag serviria resultado do backend anterior por 1h e o
        # A/B em produção estaria medindo o cache.
        mock_db_conn("src.routes.rag.get_db_conn")
        get = mocker.patch("src.routes.rag.redis_cache.cache_get", return_value=None)
        mocker.patch("src.routes.rag.redis_cache.cache_set")
        emb = mocker.MagicMock()
        emb.data = [mocker.MagicMock(embedding=[0.1])]
        fake = mocker.MagicMock()
        fake.embeddings.create.return_value = emb
        mocker.patch("src.routes.rag._get_client", return_value=fake)
        mocker.patch("src.routes.rag.queries.busca_semantica", return_value=[])
        mocker.patch("src.routes.rag.vector.busca_semantica", return_value=[])

        mocker.patch.object(Config, "RAG_BACKEND", "pgvector")
        client.post("/rag/busca", json={"pergunta": "DAS?", "perfil": "mei"})
        mocker.patch.object(Config, "RAG_BACKEND", "upstash")
        client.post("/rag/busca", json={"pergunta": "DAS?", "perfil": "mei"})

        assert get.call_args_list[0].args[0] != get.call_args_list[1].args[0]
