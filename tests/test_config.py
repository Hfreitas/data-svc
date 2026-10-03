"""Testes dos defaults de Config que já causaram falha silenciosa em produção."""
import importlib

import dotenv
import pytest

import src.config


@pytest.fixture
def config_sem_env(monkeypatch):
	"""Recarrega src.config com o ambiente limpo da var pedida.

	`Config` lê `os.environ` no import, então testar um default exige reload.
	`load_dotenv` também precisa virar no-op: sem isso um `.env` na máquina de
	quem roda o teste injetaria o valor e o teste mediria a máquina em vez do
	código. Não é hipotético — o `.env` deste repo tem `RAG_MATCH_THRESHOLD=0.7`
	e foi ele que fez a primeira versão deste teste falhar contra o código já
	corrigido.

	O patch vai em `dotenv.load_dotenv`, não em `src.config.load_dotenv`: o
	reload reexecuta `from dotenv import load_dotenv`, o que reata o nome à
	função verdadeira e desfaria um patch aplicado no módulo de destino.
	"""

	def _reload(*vars_a_limpar: str):
		for var in vars_a_limpar:
			monkeypatch.delenv(var, raising=False)
		monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
		return importlib.reload(src.config).Config

	yield _reload
	# devolve o módulo ao estado do resto da suíte. `undo()` antes do reload é
	# obrigatório: sem ele o módulo ficaria recarregado com `load_dotenv`
	# neutralizado e as vars do `.env` sumiriam para quem rodar depois.
	monkeypatch.undo()
	importlib.reload(src.config)


def test_threshold_default_e_0_4(config_sem_env):
	"""0.7 zerava o retrieval com text-embedding-3-small.

	Medido em 2026-08-17 nos dois backends: recall 0,92 a 0,4 e 0,84 a 0,5,
	com vazamento 0,0% em ambos — subir o corte não compra precisão, só apaga
	resultado. A 0.7 a rota devolve `200 {"resultados": []}`, sem erro nenhum:
	o serviço parece saudável e o agente responde sem fundamento.
	"""
	Config = config_sem_env("RAG_MATCH_THRESHOLD")

	assert Config.RAG_MATCH_THRESHOLD == 0.4


def test_threshold_respeita_env(config_sem_env, monkeypatch):
	"""O default não pode passar por cima de quem setou a var."""
	config_sem_env("RAG_MATCH_THRESHOLD")
	monkeypatch.setenv("RAG_MATCH_THRESHOLD", "0.55")

	Config = importlib.reload(src.config).Config

	assert Config.RAG_MATCH_THRESHOLD == 0.55
