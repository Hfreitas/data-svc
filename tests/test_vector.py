"""Backend Upstash Vector do /rag/busca.

Os números deste arquivo não são inventados: saem do A/B medido em 17/08 contra o
índice real (repo `meire`, `docs/rag-upstash-vector-plano.md` F5), onde pgvector e
Upstash empataram em recall 0,92 com zero divergência nos 31 casos do golden — mas
só depois de neutralizar escala de score e busca aproximada. Estes testes existem
para essas duas correções não se perderem na travessia para cá.
"""
import json
import urllib.error
from contextlib import contextmanager

import pytest

from src import vector
from src.config import Config


@pytest.fixture
def habilitado(mocker):
    mocker.patch.object(Config, "UPSTASH_VECTOR_REST_URL", "https://fake.upstash.io")
    mocker.patch.object(Config, "UPSTASH_VECTOR_REST_TOKEN", "tok")


def _mock_urlopen(mocker, result):
    resp = mocker.MagicMock()
    resp.read.return_value = json.dumps({"result": result}).encode("utf-8")

    @contextmanager
    def _cm(req, *args, **kwargs):
        _cm.req = req
        yield resp

    return mocker.patch("src.vector.urllib.request.urlopen", side_effect=_cm)


def _corpo(spy) -> dict:
    """Body JSON da última requisição feita pelo urlopen mockado."""
    return json.loads(spy.call_args.args[0].data)


def _url(spy) -> str:
    return spy.call_args.args[0].full_url


def _hit(id_, score):
    return {"id": id_, "score": score, "data": f"texto {id_}", "metadata": {"perfil": ["mei"]}}


class TestNamespace:
    def test_perfil_vira_namespace_no_path(self, habilitado, mocker):
        spy = _mock_urlopen(mocker, [])
        vector.busca_semantica([0.1], 0.4, 5, "mei")
        assert _url(spy).endswith("/query/mei")

    def test_profissional_liberal_normaliza_para_pl(self, habilitado, mocker):
        # o índice e o golden usam `pl`; o Orbit manda `profissional_liberal`.
        # Namespace inexistente na Upstash não é erro — devolve vazio, e a falha
        # vira 200 com zero resultados.
        spy = _mock_urlopen(mocker, [])
        vector.busca_semantica([0.1], 0.4, 5, "profissional_liberal")
        assert _url(spy).endswith("/query/pl")

    def test_perfil_invalido_e_erro_nao_busca_vazio(self, habilitado, mocker):
        # sem perfil válido não existe namespace equivalente a "tudo": o default
        # ("") tem zero vetores. Buscar nele devolveria 200 vazio silencioso, então
        # o backend recusa e o caller decide (cai no pgvector).
        spy = _mock_urlopen(mocker, [])
        with pytest.raises(vector.VectorIndisponivel):
            vector.busca_semantica([0.1], 0.4, 5, None)
        spy.assert_not_called()


class TestEscalaEOverfetch:
    def test_score_volta_para_escala_de_cosseno(self, habilitado, mocker):
        # medido: mesmo chunk, "quando vence o DAS?" -> 0,421097 no pgvector e
        # 0,710548 na Upstash. Ela normaliza cosseno como (1+cos)/2.
        _mock_urlopen(mocker, [_hit("a", 0.710548)])
        r = vector.busca_semantica([0.1], 0.4, 5, "mei")
        assert r[0]["similarity"] == pytest.approx(0.421096)

    def test_threshold_corta_na_escala_convertida(self, habilitado, mocker):
        # sem a conversão, threshold 0,4 cru aceitaria tudo acima de cosseno -0,20,
        # ou seja o topK inteiro — o índice deixaria de filtrar qualquer coisa.
        _mock_urlopen(mocker, [_hit("a", 0.705), _hit("b", 0.695)])
        r = vector.busca_semantica([0.1], 0.4, 5, "mei")
        assert [x["id"] for x in r] == ["a"]

    def test_pede_mais_que_count_porque_a_busca_e_aproximada(self, habilitado, mocker):
        # HNSW: o feixe de exploração sai do topK. Medido no índice real, topK<=10
        # perdia o vizinho verdadeiro (cos 0,601) e devolvia chunks a 0,377; com
        # topK=20 ele voltava em 1º. 4 dos 31 casos do golden tinham top-5 incompleto.
        spy = _mock_urlopen(mocker, [])
        vector.busca_semantica([0.1], 0.4, 5, "mei")
        assert _corpo(spy)["topK"] == 5 * vector.FATOR_OVERFETCH

    def test_trunca_no_count_pedido(self, habilitado, mocker):
        # over-fetch é precisão de busca, não mudança de contrato: quem pede 2
        # recebe no máximo 2, igual ao LIMIT do pgvector.
        _mock_urlopen(mocker, [_hit(str(i), 0.9) for i in range(9)])
        r = vector.busca_semantica([0.1], 0.4, 2, "mei")
        assert [x["id"] for x in r] == ["0", "1"]


class TestContrato:
    def test_shape_identico_ao_pgvector(self, habilitado, mocker):
        # a rota devolve id/content/similarity; qualquer chave a mais ou a menos
        # muda o contrato que os nós do n8n já consomem.
        _mock_urlopen(mocker, [_hit("a", 0.9)])
        r = vector.busca_semantica([0.1], 0.4, 5, "mei")
        assert set(r[0]) == {"id", "content", "similarity"}
        assert r[0]["content"] == "texto a"

    def test_pede_o_texto_de_volta(self, habilitado, mocker):
        # o texto vive em `data` (não em metadata); sem includeData o content
        # voltaria vazio e o agente responderia sem fundamento nenhum.
        spy = _mock_urlopen(mocker, [])
        vector.busca_semantica([0.1], 0.4, 5, "mei")
        assert _corpo(spy)["includeData"] is True


class TestFalha:
    def test_erro_http_levanta_em_vez_de_devolver_vazio(self, habilitado, mocker):
        # devolver [] aqui seria o pior dos mundos: 200 sem fundamento, com a
        # Upstash parecendo saudável. Levanta e o caller cai no pgvector.
        mocker.patch(
            "src.vector.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("u", 500, "erro", {}, None),
        )
        with pytest.raises(vector.VectorIndisponivel):
            vector.busca_semantica([0.1], 0.4, 5, "mei")

    def test_sem_credencial_levanta(self, mocker):
        mocker.patch.object(Config, "UPSTASH_VECTOR_REST_URL", "")
        spy = mocker.patch("src.vector.urllib.request.urlopen")
        with pytest.raises(vector.VectorIndisponivel):
            vector.busca_semantica([0.1], 0.4, 5, "mei")
        spy.assert_not_called()
