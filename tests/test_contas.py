class TestUpsertContaRecorrente:
    def test_upsert_conta_com_payload_valido(self, client, mock_db_conn, mocker):
        usuario_id = 1
        payload = {
            "tipo": "internet",
            "descricao": "Plano fibra",
            "valor": "129.90",
            "dia_vencimento": 10,
            "lembrete_ativo": "true",
            "pix_chave": "contato@empresa.com",
        }
        conta_fake = {
            "id": 100,
            "tipo": "internet",
            "descricao": "Plano fibra",
            "valor": 129.9,
            "dia_vencimento": 10,
            "lembrete_ativo": True,
        }
        _, conn = mock_db_conn("src.routes.contas.get_db_conn")

        upsert_mock = mocker.patch("src.routes.contas.q.upsert", return_value=conta_fake)

        resp = client.post(f"/usuarios/{usuario_id}/contas-recorrentes", json=payload)

        assert resp.status_code == 200
        assert resp.get_json() == conta_fake
        upsert_mock.assert_called_once()
        args = upsert_mock.call_args.args
        assert args[0] is conn
        assert args[1] == usuario_id
        assert args[2]["tipo"] == "internet"
        assert args[2]["dia_vencimento"] == 10
        assert args[2]["lembrete_ativo"] is True

    def test_retorna_400_quando_body_nao_for_json_objeto(self, client):
        resp = client.post(
            "/usuarios/1/contas-recorrentes",
            data="nao-json",
            content_type="text/plain",
        )

        assert resp.status_code == 400
        assert resp.get_json() == {
            "error": "body_invalido",
            "detail": "JSON inválido ou ausente",
        }

    def test_retorna_400_sem_campos_obrigatorios(self, client):
        resp = client.post("/usuarios/1/contas-recorrentes", json={})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "campos obrigatórios ausentes:" in data["detail"]

    def test_retorna_400_quando_tipo_for_invalido(self, client):
        payload = {
            "tipo": "streaming",
            "descricao": "Assinatura",
            "valor": "39.90",
            "dia_vencimento": 12,
        }

        resp = client.post("/usuarios/1/contas-recorrentes", json=payload)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "o campo 'tipo' está inválido" in data["detail"]

    def test_retorna_400_quando_dia_vencimento_for_invalido(self, client):
        payload = {
            "tipo": "luz",
            "descricao": "Conta de energia",
            "valor": "220.00",
            "dia_vencimento": 35,
        }

        resp = client.post("/usuarios/1/contas-recorrentes", json=payload)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "o campo 'dia_vencimento' deve ser inteiro entre 1 e 31" in data["detail"]

    def test_retorna_400_quando_lembrete_ativo_for_invalido(self, client):
        payload = {
            "tipo": "agua",
            "descricao": "Conta de agua",
            "valor": "95.50",
            "dia_vencimento": 5,
            "lembrete_ativo": "talvez",
        }

        resp = client.post("/usuarios/1/contas-recorrentes", json=payload)

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "o campo 'lembrete_ativo' deve ser booleano" in data["detail"]
