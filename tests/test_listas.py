from src.config import Config


class TestListListas:
    def test_lista_listas_do_usuario(self, client, mock_db_conn, mocker):
        usuario_id = 1
        listas_fake = [
            {"id": 10, "nome_lista": "Mercado", "total_itens": 3},
            {"id": 11, "nome_lista": "Farmacia", "total_itens": 1},
        ]
        _, conn = mock_db_conn("src.routes.listas.get_db_conn")

        mocker.patch("src.routes.listas.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.listas.q.list_listas", return_value=listas_fake)
        cache_set_mock = mocker.patch("src.routes.listas.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/listas")

        assert resp.status_code == 200
        assert resp.get_json() == listas_fake
        list_mock.assert_called_once_with(conn, usuario_id)
        cache_set_mock.assert_called_once_with(
            "listas",
            usuario_id,
            listas_fake,
            Config.CACHE_TTL_LISTAS,
        )

    def test_usa_cache_na_segunda_chamada_listas(self, client, mock_db_conn, mocker):
        usuario_id = 1
        listas_fake = [{"id": 10, "nome_lista": "Mercado", "total_itens": 3}]
        get_db_conn_mock, conn = mock_db_conn("src.routes.listas.get_db_conn")

        cache_get_mock = mocker.patch(
            "src.routes.listas.cache_get",
            side_effect=[None, listas_fake],
        )
        list_mock = mocker.patch("src.routes.listas.q.list_listas", return_value=listas_fake)
        mocker.patch("src.routes.listas.cache_set")

        resp_1 = client.get(f"/usuarios/{usuario_id}/listas")
        resp_2 = client.get(f"/usuarios/{usuario_id}/listas")

        assert resp_1.status_code == 200
        assert resp_2.status_code == 200
        assert resp_1.get_json() == listas_fake
        assert resp_2.get_json() == listas_fake
        assert cache_get_mock.call_count == 2
        list_mock.assert_called_once_with(conn, usuario_id)
        get_db_conn_mock.assert_called_once()


class TestListItens:
    def test_lista_itens_da_lista(self, client, mock_db_conn, mocker):
        usuario_id = 1
        lista_id = 10
        itens_fake = [
            {
                "id": 101,
                "nome_item": "arroz",
                "quantidade": "2",
                "preco_unitario": "10.00",
                "preco_total": "20.00",
            }
        ]
        _, conn = mock_db_conn("src.routes.listas.get_db_conn")

        mocker.patch("src.routes.listas.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.listas.q.list_itens", return_value=itens_fake)
        cache_set_mock = mocker.patch("src.routes.listas.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/listas/{lista_id}/itens")

        assert resp.status_code == 200
        assert resp.get_json() == itens_fake
        list_mock.assert_called_once_with(conn, lista_id, usuario_id)
        cache_set_mock.assert_called_once_with(
            "itens_lista",
            lista_id,
            itens_fake,
            Config.CACHE_TTL_LISTAS,
        )

    def test_usa_cache_na_segunda_chamada_itens(self, client, mock_db_conn, mocker):
        usuario_id = 1
        lista_id = 10
        itens_fake = [{"id": 101, "nome_item": "arroz", "quantidade": "2"}]
        get_db_conn_mock, conn = mock_db_conn("src.routes.listas.get_db_conn")

        cache_get_mock = mocker.patch(
            "src.routes.listas.cache_get",
            side_effect=[None, itens_fake],
        )
        list_mock = mocker.patch("src.routes.listas.q.list_itens", return_value=itens_fake)
        mocker.patch("src.routes.listas.cache_set")

        resp_1 = client.get(f"/usuarios/{usuario_id}/listas/{lista_id}/itens")
        resp_2 = client.get(f"/usuarios/{usuario_id}/listas/{lista_id}/itens")

        assert resp_1.status_code == 200
        assert resp_2.status_code == 200
        assert resp_1.get_json() == itens_fake
        assert resp_2.get_json() == itens_fake
        assert cache_get_mock.call_count == 2
        list_mock.assert_called_once_with(conn, lista_id, usuario_id)
        get_db_conn_mock.assert_called_once()


class TestUpsertItens:
    def test_upsert_itens_da_lista(self, client, mock_db_conn, mocker):
        usuario_id = 1
        lista_id = 10
        payload = {
            "itens": [
                {"nome_item": "Arroz", "quantidade": "2", "preco_unitario": "10.00"},
                {"nome_item": "Feijao", "quantidade": "1", "preco_unitario": "8.50"},
            ]
        }
        itens_upsertados = [
            {"nome_item": "arroz", "quantidade": "2", "preco_unitario": "10.00"},
            {"nome_item": "feijao", "quantidade": "1", "preco_unitario": "8.50"},
        ]
        _, conn = mock_db_conn("src.routes.listas.get_db_conn")

        upsert_mock = mocker.patch("src.routes.listas.q.upsert_itens", return_value=itens_upsertados)
        invalidate_mock = mocker.patch("src.routes.listas.cache_invalidate")

        resp = client.post(f"/usuarios/{usuario_id}/listas/{lista_id}/itens", json=payload)

        assert resp.status_code == 200
        assert resp.get_json() == itens_upsertados
        upsert_mock.assert_called_once()
        args = upsert_mock.call_args.args
        assert args[0] is conn
        assert args[1] == lista_id
        assert args[2] == usuario_id
        assert args[3] == [
            {"nome_item": "Arroz", "quantidade": "2", "preco_unitario": "10.00"},
            {"nome_item": "Feijao", "quantidade": "1", "preco_unitario": "8.50"},
        ]
        invalidate_mock.assert_called_once_with("itens_lista", lista_id)

    def test_retorna_400_quando_body_nao_for_json_objeto(self, client):
        usuario_id = 1
        lista_id = 10

        resp = client.post(
            f"/usuarios/{usuario_id}/listas/{lista_id}/itens",
            data="nao-json",
            content_type="text/plain",
        )

        assert resp.status_code == 400
        assert resp.get_json() == {
            "error": "body_invalido",
            "detail": "JSON inválido ou ausente",
        }

    def test_retorna_400_sem_itens_validos(self, client):
        usuario_id = 1
        lista_id = 10

        resp = client.post(
            f"/usuarios/{usuario_id}/listas/{lista_id}/itens",
            json={"itens": []},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "o campo 'itens' deve ser um array com pelo menos um item" in data["detail"]


class TestDeleteItens:
    def test_remove_itens_da_lista(self, client, mock_db_conn, mocker):
        usuario_id = 1
        lista_id = 10
        payload = {"nomes": [" arroz ", "Feijao"]}
        removidos = ["arroz", "feijao"]
        _, conn = mock_db_conn("src.routes.listas.get_db_conn")

        delete_mock = mocker.patch("src.routes.listas.q.delete_itens", return_value=removidos)
        invalidate_mock = mocker.patch("src.routes.listas.cache_invalidate")

        resp = client.delete(f"/usuarios/{usuario_id}/listas/{lista_id}/itens", json=payload)

        assert resp.status_code == 200
        assert resp.get_json() == {"removidos": removidos}
        delete_mock.assert_called_once_with(conn, lista_id, usuario_id, ["arroz", "feijao"])
        invalidate_mock.assert_called_once_with("itens_lista", lista_id)

    def test_retorna_400_sem_nomes_validos(self, client):
        usuario_id = 1
        lista_id = 10

        resp = client.delete(
            f"/usuarios/{usuario_id}/listas/{lista_id}/itens",
            json={"nomes": []},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "o campo 'nomes' deve ser um array com pelo menos um item" in data["detail"]
