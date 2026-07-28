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

    def test_retorna_400_quando_bairro_id_ausente(self, client):
        resp = client.get(
            "/comunidade/profissionais/ranking",
            query_string={"categoria": "motoboy", "solicitante_id": 5},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "bairro_id" in data["detail"]

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
