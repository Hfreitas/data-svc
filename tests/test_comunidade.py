import pytest

from src.cache import cache_invalidate
from src.routes.comunidade import _BAIRRO_NS


@pytest.fixture(autouse=True)
def _limpa_cache_bairro():
    # O cache de bairro é L1 de processo e vive entre testes; sem isso um teste
    # contamina o próximo (o 404 do miss viraria hit do teste anterior).
    cache_invalidate(_BAIRRO_NS)
    yield
    cache_invalidate(_BAIRRO_NS)


class TestRankingProfissionais:
    def test_ranking_retorna_200_com_lista_mockada(self, client, mock_db_conn, mocker):
        resultado_fake = [
            {
                "profissional_id": 10,
                "nome": "Fulano",
                "servico_categoria": "motoboy",
                "servico_descricao": "Entrego rápido",
                "bairro": "Centro",
                "distancia_km": 1.2,
                "conexao_id": "11111111-1111-1111-1111-111111111111",
            }
        ]
        _, conn = mock_db_conn("src.routes.comunidade.get_db_conn")
        ranking_mock = mocker.patch("src.routes.comunidade.q.ranking", return_value=resultado_fake)

        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "categoria": "motoboy", "solicitante_id": 5},
        )

        assert resp.status_code == 200
        assert resp.get_json() == resultado_fake
        ranking_mock.assert_called_once()
        assert ranking_mock.call_args.args[0] is conn
        kwargs = ranking_mock.call_args.kwargs
        assert kwargs["bairro_id"] == 1
        assert kwargs["categoria"] == "motoboy"
        assert kwargs["solicitante_id"] == 5
        assert kwargs["limite"] == 3

    @pytest.mark.parametrize("query_extra", [{}, {"bairro_id": "0"}, {"bairro_id": ""}])
    def test_sem_bairro_busca_por_categoria_e_devolve_distancia_nula(
        self, client, mock_db_conn, mocker, query_extra
    ):
        """Participação na Comunidade é automática e ninguém informa bairro no
        onboarding, então quase toda a rede tem bairro_id NULL. `0` é o que o nó
        `Prep Params Comunidade` manda quando não resolveu bairro — os três casos
        têm que chegar como None na query, não virar 400.
        """
        resultado_fake = [
            {
                "profissional_id": 10,
                "nome": "Fulano",
                "servico_categoria": "motoboy",
                "servico_descricao": None,
                "bairro": None,
                "distancia_km": None,
                "conexao_id": "11111111-1111-1111-1111-111111111111",
            }
        ]
        mock_db_conn("src.routes.comunidade.get_db_conn")
        ranking_mock = mocker.patch("src.routes.comunidade.q.ranking", return_value=resultado_fake)

        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"categoria": "motoboy", "solicitante_id": 5, **query_extra},
        )

        assert resp.status_code == 200
        assert resp.get_json() == resultado_fake
        assert ranking_mock.call_args.kwargs["bairro_id"] is None

    def test_retorna_400_quando_bairro_id_nao_numerico(self, client):
        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": "abc", "categoria": "motoboy", "solicitante_id": 5},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "bairro_id" in data["detail"]

    def test_retorna_400_quando_categoria_ausente(self, client):
        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "solicitante_id": 5},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "categoria" in data["detail"]

    def test_retorna_400_quando_categoria_fora_do_vocabulario(self, client):
        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "categoria": "astrologia", "solicitante_id": 5},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "categoria" in data["detail"]

    def test_retorna_400_quando_solicitante_id_ausente(self, client):
        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "categoria": "motoboy"},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "solicitante_id" in data["detail"]

    def test_default_limite_quando_limit_nao_informado(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        ranking_mock = mocker.patch("src.routes.comunidade.q.ranking", return_value=[])

        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "categoria": "motoboy", "solicitante_id": 5},
        )

        assert resp.status_code == 200
        assert ranking_mock.call_args.kwargs["limite"] == 3

    @pytest.mark.parametrize(
        "categoria",
        ["advogado", "contador", "dentista", "fisioterapeuta", "nutricionista",
         "psicologo", "personal_trainer"],
    )
    def test_aceita_categorias_pl_presentes_no_seed(
        self, client, mock_db_conn, mocker, categoria
    ):
        # Regressão: essas 7 existem em comunidade_profissionais mas estavam fora
        # da whitelist, então todo pedido PL levava 400.
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.ranking", return_value=[])

        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "categoria": categoria, "solicitante_id": 5},
        )

        assert resp.status_code == 200

    def test_retorna_400_quando_limit_abaixo_do_range(self, client):
        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "categoria": "motoboy", "solicitante_id": 5, "limit": 0},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "limit" in data["detail"]

    def test_retorna_400_quando_limit_acima_do_range(self, client):
        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"bairro_id": 1, "categoria": "motoboy", "solicitante_id": 5, "limit": 11},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "limit" in data["detail"]


class TestResolverBairro:
    BAIRRO = {
        "id": 1, "nome": "Centro", "cidade": "Salvador", "uf": "BA",
        "centro_lat": -12.97, "centro_lon": -38.5,
    }

    def test_por_nome_retorna_200(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch("src.routes.comunidade.q.buscar_bairro", return_value=self.BAIRRO)

        resp = client.get("/comunidade/bairros", query_string={"nome": "centro"})

        assert resp.status_code == 200
        assert resp.get_json() == self.BAIRRO
        assert buscar.call_args.args[0] is conn
        assert buscar.call_args.kwargs == {"nome": "centro", "texto": None}

    def test_por_texto_livre_retorna_200(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch("src.routes.comunidade.q.buscar_bairro", return_value=self.BAIRRO)

        resp = client.get(
            "/comunidade/bairros",
            query_string={"texto": "preciso de um eletricista no centro"},
        )

        assert resp.status_code == 200
        assert buscar.call_args.kwargs == {
            "nome": None, "texto": "preciso de um eletricista no centro",
        }

    def test_nome_prevalece_sobre_texto(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch("src.routes.comunidade.q.buscar_bairro", return_value=self.BAIRRO)

        resp = client.get(
            "/comunidade/bairros", query_string={"nome": "Pituba", "texto": "no centro"}
        )

        assert resp.status_code == 200
        assert buscar.call_args.kwargs == {"nome": "Pituba", "texto": None}

    def test_texto_e_truncado_em_500_chars(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch("src.routes.comunidade.q.buscar_bairro", return_value=self.BAIRRO)

        client.get("/comunidade/bairros", query_string={"texto": "a" * 900})

        assert len(buscar.call_args.kwargs["texto"]) == 500

    def test_segunda_chamada_vem_do_cache_sem_tocar_o_banco(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch("src.routes.comunidade.q.buscar_bairro", return_value=self.BAIRRO)

        primeira = client.get("/comunidade/bairros", query_string={"nome": "centro"})
        segunda = client.get("/comunidade/bairros", query_string={"nome": "centro"})

        assert primeira.get_json() == segunda.get_json() == self.BAIRRO
        buscar.assert_called_once()

    def test_miss_nao_e_cacheado(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch("src.routes.comunidade.q.buscar_bairro", return_value=None)

        assert client.get("/comunidade/bairros", query_string={"nome": "xpto"}).status_code == 404
        assert client.get("/comunidade/bairros", query_string={"nome": "xpto"}).status_code == 404
        assert buscar.call_count == 2

    def test_retorna_404_quando_bairro_nao_existe(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.buscar_bairro", return_value=None)

        resp = client.get("/comunidade/bairros", query_string={"nome": "xpto"})

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "bairro_nao_encontrado"

    def test_retorna_400_sem_nome_e_sem_texto(self, client):
        resp = client.get("/comunidade/bairros")

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad_request"


class TestListarConexoes:
    def test_retorna_200_com_lista(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.comunidade.get_db_conn")
        fake = [{"id": "abc", "status": "conectado", "profissional_2": {"nome": "Fulano"}}]
        listar = mocker.patch("src.routes.comunidade.q.conexoes_do_usuario", return_value=fake)

        resp = client.get("/comunidade/conexoes", query_string={"solicitante_id": 5})

        assert resp.status_code == 200
        assert resp.get_json() == fake
        assert listar.call_args.args == (conn, 5)

    def test_lista_vazia_retorna_200(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.conexoes_do_usuario", return_value=[])

        resp = client.get("/comunidade/conexoes", query_string={"solicitante_id": 5})

        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_retorna_400_sem_solicitante_id(self, client):
        resp = client.get("/comunidade/conexoes")

        assert resp.status_code == 400
        assert "solicitante_id" in resp.get_json()["detail"]


class TestConexaoPendente:
    PENDENTE = {
        "id": "11111111-1111-1111-1111-111111111111",
        "status": "aguardando_profissional",
        "solicitante_usuario_id": 5,
        "indicado_usuario_id": 9,
    }

    def test_retorna_200(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch(
            "src.routes.comunidade.q.conexao_pendente_por_telefone", return_value=self.PENDENTE
        )

        resp = client.get(
            "/comunidade/conexoes/pendente", query_string={"telefone": "5571999998888"}
        )

        assert resp.status_code == 200
        assert resp.get_json() == self.PENDENTE
        assert buscar.call_args.args == (conn, "5571999998888")

    def test_telefone_com_mascara_e_normalizado(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        buscar = mocker.patch(
            "src.routes.comunidade.q.conexao_pendente_por_telefone", return_value=self.PENDENTE
        )

        resp = client.get(
            "/comunidade/conexoes/pendente", query_string={"telefone": "+55 (71) 99999-8888"}
        )

        assert resp.status_code == 200
        assert buscar.call_args.args[1] == "5571999998888"

    def test_retorna_404_quando_nao_ha_pendencia(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.conexao_pendente_por_telefone", return_value=None)

        resp = client.get(
            "/comunidade/conexoes/pendente", query_string={"telefone": "5571999998888"}
        )

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "conexao_pendente_nao_encontrada"

    def test_retorna_400_com_telefone_curto(self, client):
        resp = client.get("/comunidade/conexoes/pendente", query_string={"telefone": "123"})

        assert resp.status_code == 400
        assert "telefone" in resp.get_json()["detail"]


class TestResponderConexao:
    CONEXAO_ID = "11111111-1111-1111-1111-111111111111"

    def test_etapa_1_resposta_true_chama_responder_solicitante(self, client, mock_db_conn, mocker):
        resultado_fake = {"id": self.CONEXAO_ID, "status": "aguardando_profissional"}
        mock_db_conn("src.routes.comunidade.get_db_conn")
        solicitante_mock = mocker.patch(
            "src.routes.comunidade.q.responder_solicitante", return_value=resultado_fake
        )
        profissional_mock = mocker.patch("src.routes.comunidade.q.responder_profissional")

        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 1, "resposta": True},
        )

        assert resp.status_code == 200
        assert resp.get_json() == resultado_fake
        solicitante_mock.assert_called_once()
        profissional_mock.assert_not_called()

    def test_conexao_id_chega_na_query_como_str(self, client, mock_db_conn, mocker):
        """Regressão: o converter <uuid:...> entrega uuid.UUID, que psycopg2 não
        adapta ("can't adapt type 'UUID'") — a rota virava 500 em produção."""
        mock_db_conn("src.routes.comunidade.get_db_conn")
        solicitante_mock = mocker.patch(
            "src.routes.comunidade.q.responder_solicitante",
            return_value={"id": self.CONEXAO_ID, "status": "aguardando_profissional"},
        )

        client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 1, "resposta": True},
        )

        recebido = solicitante_mock.call_args.args[1]
        assert isinstance(recebido, str)
        assert recebido == self.CONEXAO_ID

    def test_etapa_1_resposta_false_retorna_200(self, client, mock_db_conn, mocker):
        resultado_fake = {"id": self.CONEXAO_ID, "status": "recusado_solicitante"}
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.responder_solicitante", return_value=resultado_fake)

        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 1, "resposta": False},
        )

        assert resp.status_code == 200
        assert resp.get_json() == resultado_fake

    def test_etapa_2_resposta_true_chama_responder_profissional(self, client, mock_db_conn, mocker):
        resultado_fake = {"id": self.CONEXAO_ID, "status": "conectado"}
        mock_db_conn("src.routes.comunidade.get_db_conn")
        solicitante_mock = mocker.patch("src.routes.comunidade.q.responder_solicitante")
        profissional_mock = mocker.patch(
            "src.routes.comunidade.q.responder_profissional", return_value=resultado_fake
        )

        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 2, "resposta": True},
        )

        assert resp.status_code == 200
        assert resp.get_json() == resultado_fake
        profissional_mock.assert_called_once()
        solicitante_mock.assert_not_called()

    def test_etapa_2_resposta_false_retorna_200(self, client, mock_db_conn, mocker):
        resultado_fake = {"id": self.CONEXAO_ID, "status": "recusado_profissional"}
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.responder_profissional", return_value=resultado_fake)

        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 2, "resposta": False},
        )

        assert resp.status_code == 200
        assert resp.get_json() == resultado_fake

    def test_etapa_2_default_conecta(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        prof = mocker.patch(
            "src.routes.comunidade.q.responder_profissional",
            return_value={"id": self.CONEXAO_ID, "status": "conectado"},
        )

        client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 2, "resposta": True},
        )

        assert prof.call_args.kwargs["conectar"] is True

    def test_etapa_2_conectar_false_registra_aceite_sem_fechar(
        self, client, mock_db_conn, mocker
    ):
        # Aceite do indicado: profissional_resposta=true mas status segue
        # aguardando_profissional, senão o evento 'indicado_aceitou' some.
        mock_db_conn("src.routes.comunidade.get_db_conn")
        prof = mocker.patch(
            "src.routes.comunidade.q.responder_profissional",
            return_value={"id": self.CONEXAO_ID, "status": "aguardando_profissional"},
        )

        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 2, "resposta": True, "conectar": False},
        )

        assert resp.status_code == 200
        assert prof.call_args.kwargs["conectar"] is False

    def test_conectar_invalido_retorna_400(self, client):
        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 2, "resposta": True, "conectar": "talvez"},
        )

        assert resp.status_code == 400
        assert "conectar" in resp.get_json()["detail"]

    def test_retorna_404_quando_mock_retorna_none(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.responder_solicitante", return_value=None)

        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 1, "resposta": True},
        )

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "conexao_nao_encontrada_para_transicao"

    def test_retorna_400_quando_body_nao_for_json_objeto(self, client):
        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            data="not json",
            content_type="text/plain",
        )

        assert resp.status_code == 400
        assert resp.get_json() == {
            "error": "body_invalido",
            "detail": "JSON inválido ou ausente",
        }

    def test_retorna_400_quando_body_e_lista_json(self, client):
        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json=[1, 2, 3],
        )

        assert resp.status_code == 400
        assert resp.get_json() == {
            "error": "body_invalido",
            "detail": "JSON inválido ou ausente",
        }

    def test_retorna_400_quando_etapa_ausente(self, client):
        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"resposta": True},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "etapa" in data["detail"]

    def test_retorna_400_quando_etapa_invalida(self, client):
        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 3, "resposta": True},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "etapa" in data["detail"]

    def test_retorna_400_quando_resposta_nao_e_booleano_valido(self, client):
        resp = client.patch(
            f"/comunidade/conexoes/{self.CONEXAO_ID}/resposta",
            json={"etapa": 1, "resposta": "talvez"},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "resposta" in data["detail"]


class TestCancelarConexoes:
    def test_cancela_por_solicitante_retorna_200(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.comunidade.get_db_conn")
        canceladas = [{"id": "a", "status": "recusado_solicitante"}]
        cancel = mocker.patch(
            "src.routes.comunidade.q.cancelar_conexoes", return_value=canceladas
        )

        resp = client.post("/comunidade/conexoes/cancelar", json={"solicitante_id": 5})

        assert resp.status_code == 200
        assert resp.get_json() == canceladas
        assert cancel.call_args.args == (conn, 5, None)

    def test_cancela_com_conexao_id(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        cancel = mocker.patch("src.routes.comunidade.q.cancelar_conexoes", return_value=[])

        resp = client.post(
            "/comunidade/conexoes/cancelar",
            json={"solicitante_id": 5, "conexao_id": "11111111-1111-1111-1111-111111111111"},
        )

        assert resp.status_code == 200
        assert cancel.call_args.args[2] == "11111111-1111-1111-1111-111111111111"

    def test_nada_para_cancelar_retorna_200_lista_vazia(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.comunidade.get_db_conn")
        mocker.patch("src.routes.comunidade.q.cancelar_conexoes", return_value=[])

        resp = client.post("/comunidade/conexoes/cancelar", json={"solicitante_id": 5})

        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_retorna_400_sem_solicitante_id(self, client):
        resp = client.post("/comunidade/conexoes/cancelar", json={})

        assert resp.status_code == 400
        assert "solicitante_id" in resp.get_json()["detail"]

    def test_retorna_400_body_nao_json(self, client):
        resp = client.post(
            "/comunidade/conexoes/cancelar", data="x", content_type="text/plain"
        )

        assert resp.status_code == 400
        assert resp.get_json()["error"] == "body_invalido"
