from datetime import date, timedelta

from src.config import Config


class TestGetSaldo:
    def test_retorna_saldo_do_mes(self, client, mock_db_conn, mocker):
        usuario_id = 1
        mes = date.today().strftime("%Y-%m")
        saldo_fake = {
            "total_vendas": 300.0,
            "total_gastos": 120.0,
            "saldo": 180.0,
        }
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")

        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        get_saldo_mock = mocker.patch("src.routes.comprovantes.q.get_saldo", return_value=saldo_fake)
        cache_set_mock = mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/saldo?mes={mes}")

        assert resp.status_code == 200
        assert resp.get_json() == saldo_fake
        get_saldo_mock.assert_called_once_with(conn, usuario_id, mes)
        cache_set_mock.assert_called_once_with(
            "saldo",
            f"{usuario_id}:{mes}",
            saldo_fake,
            Config.CACHE_TTL_SALDO,
        )

    def test_retorna_400_sem_mes(self, client):
        resp = client.get("/usuarios/1/saldo")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "parâmetro 'mes' deve estar no formato YYYY-MM" in data["detail"]

    def test_retorna_400_mes_formato_invalido(self, client):
        resp = client.get("/usuarios/1/saldo?mes=03-2026")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
        assert "parâmetro 'mes' deve estar no formato YYYY-MM" in data["detail"]


class TestListComprovantes:
    def test_lista_todos_com_modo_relatorio(self, client, mock_db_conn, mocker):
        usuario_id = 1
        mes = date.today().strftime("%Y-%m")
        modo = "relatorio"
        comprovantes_fake = [
            {"id": 1, "operacao": "venda", "item": "Produto A", "valor_total": 100.0},
            {"id": 2, "operacao": "gasto", "item": "Insumo B", "valor_total": 60.0},
        ]
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")

        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.comprovantes.q.list_comprovantes", return_value=comprovantes_fake)
        cache_set_mock = mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/comprovantes?mes={mes}&modo={modo}")

        assert resp.status_code == 200
        assert resp.get_json() == comprovantes_fake
        list_mock.assert_called_once_with(conn, usuario_id, mes, "relatorio")
        cache_set_mock.assert_called_once_with(
            "comprovantes",
            f"{usuario_id}:{mes}:{modo}",
            comprovantes_fake,
            Config.CACHE_TTL_COMPROVANTES,
        )

    def test_filtra_apenas_gastos(self, client, mock_db_conn, mocker):
        usuario_id = 1
        mes = date.today().strftime("%Y-%m")
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")

        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.comprovantes.q.list_comprovantes", return_value=[])
        mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/comprovantes?mes={mes}&modo=gastos")

        assert resp.status_code == 200
        assert resp.get_json() == []
        list_mock.assert_called_once_with(conn, usuario_id, mes, "gasto")

    def test_filtra_apenas_vendas(self, client, mock_db_conn, mocker):
        usuario_id = 1
        mes = date.today().strftime("%Y-%m")
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")

        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.comprovantes.q.list_comprovantes", return_value=[])
        mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/comprovantes?mes={mes}&modo=vendas")

        assert resp.status_code == 200
        assert resp.get_json() == []
        list_mock.assert_called_once_with(conn, usuario_id, mes, "venda")


class TestCreateComprovante:
    def test_insere_novo_comprovante(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_venda = (date.today() - timedelta(days=2)).isoformat()

        payload = {
            "operacao": "venda",
            "item": "Produto A",
            "item_hash": "hash-001",
            "quantidade": "2",
            "valor_unitario": "50.00",
            "valor_total": "100.00",
            "data_venda": data_venda,
        }
        comprovante_fake = {
            "id": 10,
            "operacao": "venda",
            "item": "Produto A",
            "valor_total": 100.0,
            "data_venda": data_venda,
            "data_compra": None,
        }
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")

        upsert_mock = mocker.patch("src.routes.comprovantes.q.upsert", return_value=comprovante_fake)
        invalidate_prefix_mock = mocker.patch("src.routes.comprovantes.cache_invalidate_prefix")

        resp = client.post(f"/usuarios/{usuario_id}/comprovantes", json=payload)

        assert resp.status_code == 200
        assert resp.get_json() == comprovante_fake
        upsert_mock.assert_called_once()
        upsert_args = upsert_mock.call_args.args
        assert upsert_args[0] is conn
        assert upsert_args[1] == usuario_id
        assert upsert_args[2]["operacao"] == "venda"
        assert upsert_args[2]["item_hash"] == payload["item_hash"]
        assert invalidate_prefix_mock.call_count == 2
        invalidate_prefix_mock.assert_any_call("saldo", f"{usuario_id}:")
        invalidate_prefix_mock.assert_any_call("comprovantes", f"{usuario_id}:")

    def test_atualiza_comprovante_existente_por_item_hash(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_venda = (date.today() - timedelta(days=2)).isoformat()

        payload = {
            "operacao": "vendas",
            "item": "Produto A",
            "item_hash": "hash-dup-001",
            "quantidade": "2",
            "valor_unitario": "50.00",
            "valor_total": "100.00",
            "data_venda": data_venda,
        }
        retorno_primeiro = {
            "id": 10,
            "operacao": "venda",
            "item": "Produto A",
            "valor_total": 100.0,
            "data_venda": data_venda,
            "data_compra": None,
        }
        retorno_segundo = {
            "id": 10,
            "operacao": "venda",
            "item": "Produto A",
            "valor_total": 120.0,
            "data_venda": data_venda,
            "data_compra": None,
        }

        mock_db_conn("src.routes.comprovantes.get_db_conn")
        upsert_mock = mocker.patch(
            "src.routes.comprovantes.q.upsert",
            side_effect=[retorno_primeiro, retorno_segundo],
        )

        resp_1 = client.post(f"/usuarios/{usuario_id}/comprovantes", json=payload)
        payload["valor_total"] = "120.00"
        resp_2 = client.post(f"/usuarios/{usuario_id}/comprovantes", json=payload)

        assert resp_1.status_code == 200
        assert resp_2.status_code == 200
        assert resp_1.get_json()["id"] == 10
        assert resp_2.get_json()["id"] == 10
        assert resp_2.get_json()["valor_total"] == 120.0
        assert upsert_mock.call_count == 2
        for call in upsert_mock.call_args_list:
            assert call.args[2]["operacao"] == "venda"
            assert call.args[2]["item_hash"] == "hash-dup-001"

    def test_invalida_cache_saldo_e_comprovantes(self, client, mock_db_conn, mocker):
        usuario_id = 1
        data_compra = (date.today() - timedelta(days=1)).isoformat()

        payload = {
            "operacao": "gasto",
            "item": "Insumo B",
            "item_hash": "hash-002",
            "quantidade": "1",
            "valor_unitario": "80.00",
            "valor_total": "80.00",
            "data_compra": data_compra,
        }
        comprovante_fake = {
            "id": 11,
            "operacao": "gasto",
            "item": "Insumo B",
            "valor_total": 80.0,
            "data_compra": data_compra,
            "data_venda": None,
        }

        mock_db_conn("src.routes.comprovantes.get_db_conn")
        mocker.patch("src.routes.comprovantes.q.upsert", return_value=comprovante_fake)
        invalidate_prefix_mock = mocker.patch("src.routes.comprovantes.cache_invalidate_prefix")

        resp = client.post(f"/usuarios/{usuario_id}/comprovantes", json=payload)

        assert resp.status_code == 200
        assert invalidate_prefix_mock.call_count == 2
        invalidate_prefix_mock.assert_any_call("saldo", f"{usuario_id}:")
        invalidate_prefix_mock.assert_any_call("comprovantes", f"{usuario_id}:")

    def test_passa_canal_venda_para_upsert(self, client, mock_db_conn, mocker):
        usuario_id = 1
        from datetime import date
        data_venda = date.today().isoformat()

        payload = {
            "operacao": "venda",
            "item": "5 pizzas",
            "item_hash": "hash-canal-001",
            "quantidade": "5",
            "valor_unitario": "40.00",
            "valor_total": "200.00",
            "data_venda": data_venda,
            "canal_venda": "iFood",
        }
        comprovante_fake = {
            "id": 20,
            "operacao": "venda",
            "item": "5 pizzas",
            "valor_total": 200.0,
            "data_venda": data_venda,
            "data_compra": None,
            "canal_venda": "iFood",
        }
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")
        upsert_mock = mocker.patch("src.routes.comprovantes.q.upsert", return_value=comprovante_fake)
        mocker.patch("src.routes.comprovantes.cache_invalidate_prefix")

        resp = client.post(f"/usuarios/{usuario_id}/comprovantes", json=payload)

        assert resp.status_code == 200
        upsert_args = upsert_mock.call_args.args
        assert upsert_args[2].get("canal_venda") == "iFood"
        assert resp.get_json()["canal_venda"] == "iFood"


class TestSaldoPorIntervalo:
    def test_saldo_por_range_chama_query_com_datas(self, client, mock_db_conn, mocker):
        usuario_id = 7
        saldo_fake = {"total_vendas": 50.0, "total_gastos": 0.0, "saldo": 50.0}
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")
        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        get_saldo_mock = mocker.patch("src.routes.comprovantes.q.get_saldo", return_value=saldo_fake)
        cache_set_mock = mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get(f"/usuarios/{usuario_id}/saldo?data_inicio=2026-08-14&data_fim=2026-08-14")

        assert resp.status_code == 200
        assert resp.get_json() == saldo_fake
        get_saldo_mock.assert_called_once_with(
            conn, usuario_id, data_inicio="2026-08-14", data_fim="2026-08-14"
        )
        cache_set_mock.assert_called_once_with(
            "saldo", f"{usuario_id}:2026-08-14:2026-08-14", saldo_fake, Config.CACHE_TTL_SALDO
        )

    def test_saldo_range_prioriza_sobre_mes(self, client, mock_db_conn, mocker):
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")
        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        get_saldo_mock = mocker.patch("src.routes.comprovantes.q.get_saldo", return_value={})
        mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get("/usuarios/1/saldo?mes=2026-01&data_inicio=2026-08-01&data_fim=2026-08-31")

        assert resp.status_code == 200
        get_saldo_mock.assert_called_once_with(
            conn, 1, data_inicio="2026-08-01", data_fim="2026-08-31"
        )

    def test_saldo_range_data_invalida_400(self, client):
        resp = client.get("/usuarios/1/saldo?data_inicio=14-08-2026&data_fim=2026-08-14")
        assert resp.status_code == 400
        assert "data_inicio" in resp.get_json()["detail"]

    def test_saldo_range_inicio_maior_que_fim_400(self, client):
        resp = client.get("/usuarios/1/saldo?data_inicio=2026-08-31&data_fim=2026-08-01")
        assert resp.status_code == 400
        assert "data_inicio" in resp.get_json()["detail"]

    def test_saldo_range_incompleto_400(self, client):
        resp = client.get("/usuarios/1/saldo?data_inicio=2026-08-01")
        assert resp.status_code == 400
        assert "data_fim" in resp.get_json()["detail"]


class TestListComprovantesPorIntervalo:
    def test_lista_por_range_chama_query_com_datas(self, client, mock_db_conn, mocker):
        usuario_id = 7
        comprovantes_fake = [{"id": 1, "operacao": "venda", "item": "X", "valor_total": 10.0}]
        _, conn = mock_db_conn("src.routes.comprovantes.get_db_conn")
        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        list_mock = mocker.patch("src.routes.comprovantes.q.list_comprovantes", return_value=comprovantes_fake)
        cache_set_mock = mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get(
            f"/usuarios/{usuario_id}/comprovantes?modo=relatorio&data_inicio=2026-08-10&data_fim=2026-08-14"
        )

        assert resp.status_code == 200
        assert resp.get_json() == comprovantes_fake
        list_mock.assert_called_once_with(
            conn, usuario_id, modo="relatorio", data_inicio="2026-08-10", data_fim="2026-08-14"
        )
        cache_set_mock.assert_called_once_with(
            "comprovantes",
            f"{usuario_id}:2026-08-10:2026-08-14:relatorio",
            comprovantes_fake,
            Config.CACHE_TTL_COMPROVANTES,
        )

    def test_lista_range_data_invalida_400(self, client):
        resp = client.get("/usuarios/1/comprovantes?modo=relatorio&data_inicio=xx&data_fim=2026-08-14")
        assert resp.status_code == 400
