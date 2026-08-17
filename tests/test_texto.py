"""Normalização de texto para busca vetorial.

O acervo e a pergunta precisam passar pela MESMA função, senão a normalização
piora o recall em vez de melhorar: medido em PRD em 2026-08-17, `carnê-leão`
achava 5 chunks (melhor 0,6017) e `carne-leao` achava zero. Normalizar só a
pergunta converteria o caso que funciona no caso que falha.
"""

from src.utils.texto import normalizar_busca


class TestNormalizarBusca:
    def test_remove_acento(self):
        assert normalizar_busca("carnê-leão") == "carne-leao"

    def test_pergunta_sem_acento_ja_esta_na_forma_normal(self):
        # o ponto inteiro da mudança: as duas formas colapsam no mesmo texto,
        # logo no mesmo embedding
        assert normalizar_busca("carne-leao") == normalizar_busca("carnê-leão")

    def test_caixa_alta_colapsa(self):
        assert normalizar_busca("CARNÊ-LEÃO") == normalizar_busca("carnê-leão")

    def test_cedilha_vira_c(self):
        assert normalizar_busca("declaração") == "declaracao"

    def test_espaco_redundante_colapsa(self):
        assert normalizar_busca("  quando   vence  o DAS?  ") == "quando vence o das?"

    def test_pontuacao_e_preservada(self):
        # não é tokenização: interrogação e hífen carregam sinal para o embedding
        assert normalizar_busca("carnê-leão?") == "carne-leao?"

    def test_forma_decomposta_e_composta_dao_o_mesmo_resultado(self):
        # "é" pode chegar como U+00E9 ou como "e" + U+0301; sem NFKD o
        # str.__eq__ das duas difere e o cache key seria distinto para o mesmo
        # texto visível
        composta = "você"
        decomposta = "vocé"
        assert normalizar_busca(composta) == normalizar_busca(decomposta) == "voce"

    def test_numero_e_simbolo_passam_intactos(self):
        assert normalizar_busca("R$ 81,90 em 2026") == "r$ 81,90 em 2026"

    def test_string_vazia_nao_quebra(self):
        assert normalizar_busca("") == ""

    def test_so_espaco_vira_vazio(self):
        assert normalizar_busca("   ") == ""
