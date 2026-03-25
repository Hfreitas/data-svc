import pytest
from src.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestGetSaldo:
    def test_retorna_saldo_do_mes(self, client):
        # TODO: implementar
        # GET /usuarios/1/saldo?mes=2026-03
        # Assertar { mes, total_vendas, total_gastos, saldo }
        pass

    def test_retorna_400_sem_mes(self, client):
        # TODO: implementar
        pass

    def test_retorna_400_mes_formato_invalido(self, client):
        # TODO: implementar
        pass


class TestListComprovantes:
    def test_lista_todos_com_modo_relatorio(self, client):
        # TODO: implementar
        pass

    def test_filtra_apenas_gastos(self, client):
        # TODO: implementar
        pass

    def test_filtra_apenas_vendas(self, client):
        # TODO: implementar
        pass


class TestCreateComprovante:
    def test_insere_novo_comprovante(self, client):
        # TODO: implementar
        pass

    def test_atualiza_comprovante_existente_por_item_hash(self, client):
        # TODO: implementar
        # Idempotência: dois POSTs com mesmo item_hash → resultado é UPDATE
        pass

    def test_invalida_cache_saldo_e_comprovantes(self, client):
        # TODO: implementar
        pass
