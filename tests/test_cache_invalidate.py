"""POST /cache/invalidate — invalidação de cache disparada de fora do processo.

Existe porque escrita que não passa pelo data-svc (SQL manual, Fase R, job
externo) não invalida nada: L1 é TTLCache in-process e L2 só é apagado pelos
handlers de `usuarios.py`. Sem este endpoint, `usuarios.estado_atual` alterado
por SQL segue servindo valor velho por até 600s (TTL do L2).
"""


class TestInvalidatePorTelefone:
    def test_invalida_l1_e_l2(self, client, mocker):
        tel = "5571999999999"
        inv = mocker.patch("src.routes.cache.cache_invalidate")
        dele = mocker.patch("src.routes.cache.redis_cache.cache_del", return_value=True)

        resp = client.post("/cache/invalidate", json={"telefones": [tel]})

        assert resp.status_code == 200
        assert resp.get_json() == {
            "invalidados": 1,
            "telefones": [tel],
            "nao_encontrados": [],
        }
        inv.assert_called_once_with("usuario", tel)
        dele.assert_called_once_with(f"user:{tel}")

    def test_nao_abre_conexao_db_sem_ids(self, client, mocker):
        """Só telefones: o endpoint não pode custar uma conexão de banco."""
        mocker.patch("src.routes.cache.cache_invalidate")
        mocker.patch("src.routes.cache.redis_cache.cache_del", return_value=True)
        conn = mocker.patch("src.routes.cache.get_db_conn")

        resp = client.post("/cache/invalidate", json={"telefones": ["5571999999999"]})

        assert resp.status_code == 200
        conn.assert_not_called()

    def test_telefone_invalido_400(self, client, mocker):
        mocker.patch("src.routes.cache.cache_invalidate")
        mocker.patch("src.routes.cache.redis_cache.cache_del")

        resp = client.post("/cache/invalidate", json={"telefones": ["abc"]})

        assert resp.status_code == 400

    def test_l2_fora_do_ar_ainda_200(self, client, mocker):
        """redis_cache é fail-open por contrato: cache indisponível não é erro."""
        tel = "5571999999999"
        inv = mocker.patch("src.routes.cache.cache_invalidate")
        mocker.patch("src.routes.cache.redis_cache.cache_del", return_value=False)

        resp = client.post("/cache/invalidate", json={"telefones": [tel]})

        assert resp.status_code == 200
        inv.assert_called_once_with("usuario", tel)


class TestInvalidatePorId:
    def test_resolve_telefone_e_invalida_as_duas_chaves(self, client, mock_db_conn, mocker):
        """A chave do L2 é por telefone, mas o UPDATE externo é por id.

        `usuarios.py` grava as duas chaves de L1 (`<tel>` e `id:<id>`); invalidar
        só uma deixaria a outra servindo dado velho.
        """
        _, conn = mock_db_conn("src.routes.cache.get_db_conn")
        mocker.patch(
            "src.routes.cache.q.find_telefones_by_ids",
            return_value={116: "5571817557824"},
        )
        inv = mocker.patch("src.routes.cache.cache_invalidate")
        dele = mocker.patch("src.routes.cache.redis_cache.cache_del", return_value=True)

        resp = client.post("/cache/invalidate", json={"usuario_ids": [116]})

        assert resp.status_code == 200
        assert resp.get_json()["invalidados"] == 1
        assert resp.get_json()["nao_encontrados"] == []
        inv.assert_any_call("usuario", "5571817557824")
        inv.assert_any_call("usuario", "id:116")
        dele.assert_called_once_with("user:5571817557824")

    def test_id_inexistente_vai_para_nao_encontrados(self, client, mock_db_conn, mocker):
        mock_db_conn("src.routes.cache.get_db_conn")
        mocker.patch("src.routes.cache.q.find_telefones_by_ids", return_value={})
        inv = mocker.patch("src.routes.cache.cache_invalidate")
        mocker.patch("src.routes.cache.redis_cache.cache_del")

        resp = client.post("/cache/invalidate", json={"usuario_ids": [999999]})

        assert resp.status_code == 200
        assert resp.get_json() == {
            "invalidados": 0,
            "telefones": [],
            "nao_encontrados": [999999],
        }
        inv.assert_not_called()

    def test_id_nao_numerico_400(self, client):
        resp = client.post("/cache/invalidate", json={"usuario_ids": ["abc"]})
        assert resp.status_code == 400


class TestLote:
    def test_telefones_e_ids_juntos_sem_duplicar(self, client, mock_db_conn, mocker):
        """Se um id resolve para um telefone já na lista, invalida uma vez só."""
        tel = "5571999999999"
        mock_db_conn("src.routes.cache.get_db_conn")
        mocker.patch("src.routes.cache.q.find_telefones_by_ids", return_value={7: tel})
        inv = mocker.patch("src.routes.cache.cache_invalidate")
        dele = mocker.patch("src.routes.cache.redis_cache.cache_del", return_value=True)

        resp = client.post(
            "/cache/invalidate", json={"telefones": [tel], "usuario_ids": [7]}
        )

        assert resp.status_code == 200
        assert resp.get_json()["invalidados"] == 1
        dele.assert_called_once_with(f"user:{tel}")
        # a chave id: ainda precisa cair, mesmo com o telefone deduplicado
        inv.assert_any_call("usuario", "id:7")

    def test_lote_acima_do_teto_400(self, client):
        resp = client.post(
            "/cache/invalidate", json={"telefones": [f"5571{i:09d}" for i in range(501)]}
        )
        assert resp.status_code == 400


class TestBodyInvalido:
    def test_body_vazio_400(self, client):
        resp = client.post("/cache/invalidate", json={})
        assert resp.status_code == 400

    def test_body_nao_json_400(self, client):
        resp = client.post("/cache/invalidate", data="xpto", content_type="text/plain")
        assert resp.status_code == 400

    def test_campo_com_tipo_errado_400(self, client):
        resp = client.post("/cache/invalidate", json={"telefones": "5571999999999"})
        assert resp.status_code == 400
