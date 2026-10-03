import json
import urllib.error
from contextlib import contextmanager

import pytest

from src import redis_cache
from src.config import Config


@pytest.fixture
def enabled(mocker):
    """Habilita o cache (URL+token) sem prefixo de ambiente."""
    mocker.patch.object(Config, "UPSTASH_REDIS_REST_URL", "https://fake.upstash.io")
    mocker.patch.object(Config, "UPSTASH_REDIS_REST_TOKEN", "tok")
    mocker.patch.object(Config, "CACHE_ENV_PREFIX", "")


def _mock_urlopen(mocker, result):
    """Faz urlopen retornar {"result": <result>} como context manager."""
    resp = mocker.MagicMock()
    resp.read.return_value = json.dumps({"result": result}).encode("utf-8")

    @contextmanager
    def _cm(*args, **kwargs):
        yield resp

    return mocker.patch("src.redis_cache.urllib.request.urlopen", side_effect=_cm)


class TestDisabled:
    def test_get_noop(self, mocker):
        mocker.patch.object(Config, "UPSTASH_REDIS_REST_URL", "")
        spy = mocker.patch("src.redis_cache.urllib.request.urlopen")
        assert redis_cache.cache_get("user:1") is None
        spy.assert_not_called()

    def test_set_noop(self, mocker):
        mocker.patch.object(Config, "UPSTASH_REDIS_REST_URL", "")
        assert redis_cache.cache_set("k", {"a": 1}, 60) is False

    def test_dedup_never_duplicate_when_disabled(self, mocker):
        mocker.patch.object(Config, "UPSTASH_REDIS_REST_URL", "")
        assert redis_cache.dedup_is_duplicate("551199", "hash") is False


class TestGetSet:
    def test_get_hit_deserializa_json(self, enabled, mocker):
        _mock_urlopen(mocker, json.dumps({"nome": "Dandara"}))
        assert redis_cache.cache_get("user:551199") == {"nome": "Dandara"}

    def test_get_miss_result_null(self, enabled, mocker):
        _mock_urlopen(mocker, None)
        assert redis_cache.cache_get("user:551199") is None

    def test_set_ok(self, enabled, mocker):
        spy = _mock_urlopen(mocker, "OK")
        assert redis_cache.cache_set("user:1", {"a": 1}, 600) is True
        sent = json.loads(spy.call_args.args[0].data.decode("utf-8"))
        assert sent[0] == "SET" and sent[1] == "user:1"
        assert sent[3:] == ["EX", "600"]

    def test_del(self, enabled, mocker):
        _mock_urlopen(mocker, 1)
        assert redis_cache.cache_del("user:1") is True


class TestSetnxIncr:
    def test_setnx_acquired(self, enabled, mocker):
        _mock_urlopen(mocker, "OK")
        assert redis_cache.cache_setnx("dedup:x", 1, 60) is True

    def test_setnx_not_acquired(self, enabled, mocker):
        _mock_urlopen(mocker, None)  # NX falha → result null
        assert redis_cache.cache_setnx("dedup:x", 1, 60) is False

    def test_incr_first_sets_expire(self, enabled, mocker):
        spy = _mock_urlopen(mocker, 1)
        assert redis_cache.cache_incr("rl:551199", 60) == 1
        # 2 comandos: INCR + EXPIRE (result mockado é 1 nos dois; basta contar)
        assert spy.call_count == 2

    def test_incr_subsequent_no_expire(self, enabled, mocker):
        spy = _mock_urlopen(mocker, 5)
        assert redis_cache.cache_incr("rl:551199", 60) == 5
        assert spy.call_count == 1  # só INCR


class TestFailOpen:
    def test_urlerror_vira_miss(self, enabled, mocker):
        mocker.patch(
            "src.redis_cache.urllib.request.urlopen",
            side_effect=urllib.error.URLError("down"),
        )
        assert redis_cache.cache_get("user:1") is None
        assert redis_cache.cache_set("user:1", {}, 60) is False
        assert redis_cache.cache_incr("rl:1", 60) is None

    def test_api_error_vira_miss(self, enabled, mocker):
        resp = mocker.MagicMock()
        resp.read.return_value = json.dumps({"error": "WRONGPASS"}).encode("utf-8")

        @contextmanager
        def _cm(*a, **k):
            yield resp

        mocker.patch("src.redis_cache.urllib.request.urlopen", side_effect=_cm)
        assert redis_cache.cache_get("user:1") is None


class TestPrefix:
    def test_prefixo_ambiente_aplicado(self, mocker):
        mocker.patch.object(Config, "UPSTASH_REDIS_REST_URL", "https://fake.upstash.io")
        mocker.patch.object(Config, "UPSTASH_REDIS_REST_TOKEN", "tok")
        mocker.patch.object(Config, "CACHE_ENV_PREFIX", "stg")
        spy = _mock_urlopen(mocker, "OK")
        redis_cache.cache_set("user:1", {}, 60)
        sent = json.loads(spy.call_args.args[0].data.decode("utf-8"))
        assert sent[1] == "stg:user:1"


class TestGuards:
    def test_dedup_primeira_vez_processa(self, enabled, mocker):
        _mock_urlopen(mocker, "OK")  # SETNX adquire
        assert redis_cache.dedup_is_duplicate("551199", "h1") is False

    def test_dedup_repeticao_ignora(self, enabled, mocker):
        _mock_urlopen(mocker, None)  # SETNX falha (já existe)
        assert redis_cache.dedup_is_duplicate("551199", "h1") is True

    def test_rate_limit_dentro_do_limite(self, enabled, mocker):
        _mock_urlopen(mocker, 5)
        assert redis_cache.rate_limit_exceeded("551199", limit=30) is False

    def test_rate_limit_excedido(self, enabled, mocker):
        _mock_urlopen(mocker, 31)
        assert redis_cache.rate_limit_exceeded("551199", limit=30) is True
