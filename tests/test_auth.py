from src.config import Config


class TestApiAuth:
    def test_permite_request_sem_api_key_configurada(self, client, mocker):
        mocker.patch.object(Config, "API_KEY", None)

        resp = client.get("/usuarios")

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"

    def test_retorna_401_quando_api_key_ausente(self, client, mocker):
        mocker.patch.object(Config, "API_KEY", "minha-chave")

        resp = client.get("/usuarios")

        assert resp.status_code == 401
        assert resp.get_json() == {"error": "unauthorized"}

    def test_retorna_401_quando_api_key_incorreta(self, client, mocker):
        mocker.patch.object(Config, "API_KEY", "minha-chave")

        resp = client.get("/usuarios", headers={"X-API-Key": "chave-errada"})

        assert resp.status_code == 401
        assert resp.get_json() == {"error": "unauthorized"}

    def test_permite_request_quando_api_key_correta(self, client, mocker):
        mocker.patch.object(Config, "API_KEY", "minha-chave")

        resp = client.get("/usuarios", headers={"X-API-Key": "minha-chave"})

        assert resp.status_code == 400
        data = resp.get_json()
        assert data["error"] == "bad_request"
