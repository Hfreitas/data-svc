"""Testes de rota do inbox multiusuário (schema `inbox`). Query module mockado."""


class TestCreateAccount:
    def test_cria_conta_com_payload_valido(self, client, mock_db_conn, mocker):
        payload = {"phone_number": "5531999999999", "company_name": "Gabriel Distribuidora", "usuario_id": 9}
        account_fake = {
            "id": 1, "usuario_id": 9, "phone_number": "5531999999999",
            "company_name": "Gabriel Distribuidora", "status": "active", "created_at": "2026-07-29T00:00:00+00:00",
        }
        _, conn = mock_db_conn("src.routes.inbox.get_db_conn")
        create_mock = mocker.patch("src.routes.inbox.q.create_account", return_value=account_fake)

        resp = client.post("/inbox/accounts", json=payload)

        assert resp.status_code == 201
        assert resp.get_json() == account_fake
        create_mock.assert_called_once()
        args = create_mock.call_args.args
        assert args[0] is conn
        assert args[1]["phone_number"] == "5531999999999"

    def test_400_body_nao_json(self, client):
        resp = client.post("/inbox/accounts", data="x", content_type="text/plain")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "body_invalido"

    def test_400_sem_phone_number(self, client):
        resp = client.post("/inbox/accounts", json={"company_name": "X"})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "phone_number_obrigatorio"


class TestGetAccountByPhone:
    def test_resolve_conta(self, client, mock_db_conn, mocker):
        account_fake = {"id": 1, "phone_number": "5531999999999", "status": "active"}
        _, conn = mock_db_conn("src.routes.inbox.get_db_conn")
        get_mock = mocker.patch("src.routes.inbox.q.get_account_by_phone", return_value=account_fake)

        resp = client.get("/inbox/accounts/by-phone/5531999999999")

        assert resp.status_code == 200
        assert resp.get_json() == account_fake
        args = get_mock.call_args.args
        assert args[0] is conn
        assert args[1] == "5531999999999"

    def test_404_quando_nao_existe(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.inbox.get_db_conn")
        mocker.patch("src.routes.inbox.q.get_account_by_phone", return_value=None)

        resp = client.get("/inbox/accounts/by-phone/5531000000000")

        assert resp.status_code == 404
        assert resp.get_json()["error"] == "account_nao_encontrada"


class TestListConversations:
    def test_lista_com_status(self, client, mock_db_conn, mocker):
        conversas_fake = [{"id": 10, "contact_id": 5, "status": "open", "last_message": "oi"}]
        _, conn = mock_db_conn("src.routes.inbox.get_db_conn")
        list_mock = mocker.patch("src.routes.inbox.q.list_conversations", return_value=conversas_fake)

        resp = client.get("/inbox/accounts/1/conversations?status=open")

        assert resp.status_code == 200
        assert resp.get_json() == conversas_fake
        args = list_mock.call_args.args
        assert args[0] is conn
        assert args[1] == 1
        assert args[2] == "open"

    def test_lista_sem_status_passa_none(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.inbox.get_db_conn")
        list_mock = mocker.patch("src.routes.inbox.q.list_conversations", return_value=[])

        resp = client.get("/inbox/accounts/1/conversations")

        assert resp.status_code == 200
        assert list_mock.call_args.args[2] is None


class TestUpsertContact:
    def test_upsert_contato(self, client, mock_db_conn, mocker):
        payload = {"phone_number": "5531988887777", "name": "Cliente Zé"}
        contact_fake = {"id": 5, "whatsapp_account_id": 1, "phone_number": "5531988887777", "name": "Cliente Zé"}
        _, conn = mock_db_conn("src.routes.inbox.get_db_conn")
        upsert_mock = mocker.patch("src.routes.inbox.q.upsert_contact", return_value=contact_fake)

        resp = client.post("/inbox/accounts/1/contacts", json=payload)

        assert resp.status_code == 201
        assert resp.get_json() == contact_fake
        args = upsert_mock.call_args.args
        assert args[0] is conn
        assert args[1] == 1
        assert args[2]["phone_number"] == "5531988887777"

    def test_400_sem_phone_number(self, client):
        resp = client.post("/inbox/accounts/1/contacts", json={"name": "sem fone"})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "phone_number_obrigatorio"


class TestOpenConversation:
    def test_abre_conversa(self, client, mock_db_conn, mocker):
        conversa_fake = {"id": 10, "whatsapp_account_id": 1, "contact_id": 5, "status": "open"}
        _, conn = mock_db_conn("src.routes.inbox.get_db_conn")
        open_mock = mocker.patch("src.routes.inbox.q.open_or_get_conversation", return_value=conversa_fake)

        resp = client.post("/inbox/conversations", json={"account_id": 1, "contact_id": 5})

        assert resp.status_code == 201
        assert resp.get_json() == conversa_fake
        args = open_mock.call_args.args
        assert args[0] is conn
        assert args[1] == 1
        assert args[2] == 5

    def test_400_sem_ids(self, client):
        resp = client.post("/inbox/conversations", json={"account_id": 1})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "params_obrigatorios"


class TestListMessages:
    def test_lista_historico(self, client, mock_db_conn, mocker):
        msgs_fake = [{"id": 1, "content": "oi"}, {"id": 2, "content": "tudo bem?"}]
        _, conn = mock_db_conn("src.routes.inbox.get_db_conn")
        list_mock = mocker.patch("src.routes.inbox.q.list_messages", return_value=msgs_fake)

        resp = client.get("/inbox/conversations/10/messages?limit=20&before_id=100")

        assert resp.status_code == 200
        assert resp.get_json() == msgs_fake
        args = list_mock.call_args.args
        assert args[0] is conn
        assert args[1] == 10
        assert args[2] == 20
        assert args[3] == 100

    def test_limit_default_e_cap(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.inbox.get_db_conn")
        list_mock = mocker.patch("src.routes.inbox.q.list_messages", return_value=[])

        resp = client.get("/inbox/conversations/10/messages?limit=999")

        assert resp.status_code == 200
        assert list_mock.call_args.args[2] == 200  # cap em 200


class TestCreateMessage:
    def test_cria_mensagem_de_usuario(self, client, mock_db_conn, mocker):
        payload = {"conversation_id": 10, "sender_type": "user", "sender_id": 3, "content": "resposta"}
        msg_fake = {"id": 50, "conversation_id": 10, "sender_type": "user", "sender_id": 3, "content": "resposta"}
        _, conn = mock_db_conn("src.routes.inbox.get_db_conn")
        create_mock = mocker.patch("src.routes.inbox.q.create_message", return_value=msg_fake)

        resp = client.post("/inbox/messages", json=payload)

        assert resp.status_code == 201
        assert resp.get_json() == msg_fake
        args = create_mock.call_args.args
        assert args[0] is conn
        assert args[1]["sender_type"] == "user"
        assert args[1]["sender_id"] == 3

    def test_cria_mensagem_de_contato_sem_sender_id(self, client, mock_db_conn, mocker):
        payload = {"conversation_id": 10, "sender_type": "contact", "content": "oi"}
        msg_fake = {"id": 51, "sender_type": "contact", "sender_id": None}
        mock_db_conn("src.routes.inbox.get_db_conn")
        mocker.patch("src.routes.inbox.q.create_message", return_value=msg_fake)

        resp = client.post("/inbox/messages", json=payload)

        assert resp.status_code == 201

    def test_400_sem_conversation_id(self, client):
        resp = client.post("/inbox/messages", json={"sender_type": "contact", "content": "x"})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "conversation_id_obrigatorio"

    def test_400_sender_type_invalido(self, client):
        resp = client.post("/inbox/messages", json={"conversation_id": 10, "sender_type": "bot"})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "sender_type_invalido"

    def test_400_user_sem_sender_id(self, client):
        resp = client.post("/inbox/messages", json={"conversation_id": 10, "sender_type": "user", "content": "x"})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "sender_id_obrigatorio"

    def test_400_body_nao_json(self, client):
        resp = client.post("/inbox/messages", data="x", content_type="text/plain")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "body_invalido"
