import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")

os.environ.setdefault("FLASK_ENV", "development")

from src.app import create_app


@pytest.fixture
def client(mocker):
	# Evita inicialização de pool real durante os testes unitários de rota.
	mocker.patch("src.app.init_db")
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
