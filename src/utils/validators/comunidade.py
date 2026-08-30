from typing import Final

from flask import abort

from .validators import parse_boolish, require_fields


_CATEGORIAS_SERVICO: Final[set[str]] = {
    # MEI / serviços
    "motoboy", "bolos", "doces", "costura", "limpeza", "manicure",
    "cabeleireiro", "fotografia", "design_grafico", "aulas_particulares",
    "frete_mudanca", "jardinagem", "eletricista", "encanador", "pintor", "outros",
    # Profissionais liberais (mesma rede)
    "nutricionista", "psicologo", "fisioterapeuta", "dentista",
    "advogado", "contador", "personal_trainer",
}


def validate_ranking_params(args) -> dict:
    """Valida os query params do ranking de profissionais da Comunidade MEIrelles.

    Args:
        args: request.args (MultiDict) da requisição GET.

    Returns:
        Dict com bairro_id, categoria, solicitante_id, limite, servico_contexto —
        pronto para **kwargs em queries.comunidade.ranking().
    """
    try:
        bairro_id = int(args.get("bairro_id"))
        if bairro_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        abort(400, description="o parâmetro 'bairro_id' é obrigatório e deve ser um inteiro maior que zero")

    categoria = str(args.get("categoria") or "").strip().lower()
    if not categoria:
        abort(400, description="o parâmetro 'categoria' é obrigatório")
    if categoria not in _CATEGORIAS_SERVICO:
        permitidos = ", ".join(sorted(_CATEGORIAS_SERVICO))
        abort(400, description=f"o parâmetro 'categoria' está inválido. Use: {permitidos}")

    try:
        solicitante_id = int(args.get("solicitante_id"))
        if solicitante_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        abort(400, description="o parâmetro 'solicitante_id' é obrigatório e deve ser um inteiro maior que zero")

    limit_raw = args.get("limit")
    if limit_raw is None:
        limite = 3
    else:
        try:
            limite = int(limit_raw)
        except (TypeError, ValueError):
            abort(400, description="o parâmetro 'limit' deve ser um inteiro entre 1 e 10")
        if limite < 1 or limite > 10:
            abort(400, description="o parâmetro 'limit' deve ser um inteiro entre 1 e 10")

    servico_contexto = args.get("servico_contexto")

    return {
        "bairro_id": bairro_id,
        "categoria": categoria,
        "solicitante_id": solicitante_id,
        "limite": limite,
        "servico_contexto": servico_contexto,
    }


def validate_resposta_conexao_payload(body: dict) -> dict:
    """Valida o corpo da requisição de resposta (solicitante ou profissional) de uma conexão."""
    require_fields(body, "etapa", "resposta")

    try:
        etapa = int(body.get("etapa"))
    except (TypeError, ValueError):
        abort(400, description="o campo 'etapa' deve ser 1 ou 2")

    if etapa not in (1, 2):
        abort(400, description="o campo 'etapa' deve ser 1 ou 2")

    resposta = parse_boolish(body.get("resposta"), "resposta")

    return {"etapa": etapa, "resposta": resposta}
