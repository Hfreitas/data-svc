"""
Queries de contas recorrentes — funções puras que recebem conn + parâmetros e retornam rows.
"""
from psycopg2.extras import RealDictCursor

TIPOS_VALIDOS = {"aluguel", "internet", "luz", "agua", "boleto"}


def upsert(conn, usuario_id: int, data: dict) -> dict:
    params = {
        "usuario_id": usuario_id,
        "tipo": data.get("tipo"),
        "descricao": data.get("descricao"),
        "valor": data.get("valor"),
        "dia_vencimento": data.get("dia_vencimento"),
        "lembrete_ativo": data.get("lembrete_ativo", False),
        "pix_chave": data.get("pix_chave"),
    }

    sql = """
        INSERT INTO public.contas_recorrentes (
            usuario_id, tipo, descricao, valor, dia_vencimento, lembrete_ativo, pix_chave)
        VALUES (
            %(usuario_id)s,
            %(tipo)s,        -- 'aluguel' | 'internet' | 'luz' | 'agua' | 'boleto'
            %(descricao)s,
            %(valor)s,
            %(dia_vencimento)s,
            %(lembrete_ativo)s,
            %(pix_chave)s)
        ON CONFLICT (usuario_id, tipo) WHERE tipo <> 'boleto'
        DO UPDATE SET
            descricao      = EXCLUDED.descricao,
            valor          = EXCLUDED.valor,
            dia_vencimento = EXCLUDED.dia_vencimento,
            lembrete_ativo = EXCLUDED.lembrete_ativo,
            pix_chave      = EXCLUDED.pix_chave,
            updated_at     = NOW()
        RETURNING id, tipo, descricao, valor, dia_vencimento, lembrete_ativo;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row)
