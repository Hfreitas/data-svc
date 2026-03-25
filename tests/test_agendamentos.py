import pytest
from src.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestListAgendamentos:
    def test_lista_compromissos_da_semana(self, client):
        # TODO: implementar
        # GET /usuarios/1/agendamentos?semana=atual
        # Assertar lista com campos esperados
        pass

    def test_usa_cache_na_segunda_chamada(self, client):
        # TODO: implementar
        pass


class TestCreateAgendamento:
    def test_cria_compromisso(self, client):
        # TODO: implementar
        pass

    def test_retorna_400_sem_campos_obrigatorios(self, client):
        # TODO: implementar
        pass

    def test_invalida_cache_apos_criacao(self, client):
        # TODO: implementar
        pass


class TestUpdateAgendamento:
    def test_cancela_compromisso(self, client):
        # TODO: implementar
        # PUT /usuarios/1/agendamentos/5 com { status: 'cancelado' }
        pass

    def test_retorna_404_agendamento_inexistente(self, client):
        # TODO: implementar
        pass
