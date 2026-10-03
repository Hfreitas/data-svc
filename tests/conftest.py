import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")

os.environ.setdefault("FLASK_ENV", "development")
# Auth desligada nos unitários — se API_KEY vier do shell/.env, todas as rotas
# respondem 401 e os mocks de busca nunca são chamados.
os.environ.pop("API_KEY", None)
# TypeSafe RAG score off nos unitários — evita hit real se a shell tiver key/flag.
os.environ.pop("TYPESAFE_API_KEY", None)
os.environ["TYPESAFE_RAG_SCORE"] = "0"

from src.app import create_app
from src.config import Config


@pytest.fixture
def client(mocker):
	# Evita inicialização de pool real durante os testes unitários de rota.
	mocker.patch("src.app.init_db")
	# Config já pode ter lido API_KEY antes do pop acima (import residual).
	mocker.patch.object(Config, "API_KEY", None)
	mocker.patch.object(Config, "TYPESAFE_RAG_SCORE", False)
	mocker.patch.object(Config, "TYPESAFE_API_KEY", "")
	app = create_app()
	app.config["TESTING"] = True
	with app.test_client() as test_client:
		yield test_client


@pytest.fixture
def mock_db_conn(mocker):
	"""Mocka get_db_conn de qualquer rota e retorna (patch, conn_fake)."""
	def _factory(target_path: str):
		conn = object()
		ctx = mocker.MagicMock()
		ctx.__enter__.return_value = conn
		ctx.__exit__.return_value = False
		patch = mocker.patch(target_path, return_value=ctx)
		return patch, conn

	return _factory
