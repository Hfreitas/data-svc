import pytest
from src.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestGetUsuario:
    def test_retorna_usuario_existente(self, client):
        # TODO: implementar
        # Mockar q.find_by_telefone para retornar usuário fake
        # GET /usuarios?telefone=5511999999999
        # Assertar status 200 e campos do response
        pass

    def test_retorna_404_quando_nao_encontrado(self, client):
        # TODO: implementar
        pass

    def test_retorna_400_sem_telefone(self, client):
        # TODO: implementar
        pass

    def test_usa_cache_no_segundo_request(self, client):
        # TODO: implementar
        # Verificar que q.find_by_telefone é chamado apenas uma vez
        pass


class TestCreateUsuario:
    def test_cria_novo_usuario(self, client):
        # TODO: implementar
        pass

    def test_retorna_existente_se_telefone_ja_cadastrado(self, client):
        # TODO: implementar
        pass

    def test_retorna_400_sem_campos_obrigatorios(self, client):
        # TODO: implementar
        pass


class TestUpdateUsuario:
    def test_atualiza_estado_atual(self, client):
        # TODO: implementar
        pass

    def test_retorna_404_usuario_inexistente(self, client):
        # TODO: implementar
        pass

    def test_invalida_cache_apos_update(self, client):
        # TODO: implementar
        pass
