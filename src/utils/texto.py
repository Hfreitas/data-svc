import unicodedata


def normalizar_busca(texto: str) -> str:
    """Forma canônica de um texto para busca vetorial: sem acento, minúsculo,
    espaço colapsado.

    REGRA: o acervo e a pergunta têm que passar por ESTA função, os dois. Aplicar
    só de um lado piora o recall — medido em PRD em 2026-08-17, `carnê-leão`
    achava 5 chunks (melhor 0,6017) e `carne-leao` achava zero, porque o
    `text-embedding-3-small` trata a forma sem acento como outra palavra e o
    acervo só tinha a acentuada. Normalizar só a pergunta converteria o caso que
    funciona no caso que falha, sem erro nenhum aparecendo.

    NFKD separa a letra do diacrítico; `Mn` ("mark, nonspacing") é a categoria dos
    acentos soltos, então descartá-la remove o acento e preserva a letra. Isso
    também colapsa as duas formas Unicode do mesmo caractere visível (é composto
    U+00E9 vs "e" + U+0301), que de outro modo gerariam cache keys diferentes para
    o mesmo texto.

    Pontuação é preservada de propósito: não é tokenização, e "?" ou "-" carregam
    sinal para o embedding.
    """
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.lower().split())
