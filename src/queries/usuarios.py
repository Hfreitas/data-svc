from psycopg2.extras import RealDictCursor

"""
Queries de usuários — funções puras que recebem conn + parâmetros e retornam rows.
Nenhuma lógica HTTP ou de cache aqui.
"""


def find_by_telefone(conn, telefone: str) -> dict | None:
    # TODO: implementar
    # Executar SELECT por numero_telefone, retornar dict ou None
    sql = """
        SELECT
            id, numero_telefone, nome, razao_social, email,
            estado_atual, interacao_previa,
            tipo_negocio, descricao_negocio, descricao_objetivo,
            area_ajuda, preco_referencia,
            dias_trabalho, horario_inicio, horario_fim,
            data_primeiro_contato, data_ultimo_contato
        FROM public.usuarios
        WHERE numero_telefone = %(telefone)s
        LIMIT 1;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"telefone": telefone})
        row = cursor.fetchone()
        return dict(row) if row else None
    


def upsert(conn, numero_telefone: str, nome: str, razao_social: str) -> dict:
    # TODO: implementar
    # Executar CTE: existing_user + inserted_user (evita race condition)
    # Retornar dict com dados do usuário (existente ou recém-criado)
    pass


def update(conn, usuario_id: int, fields: dict) -> dict | None:
    # TODO: implementar
    # Executar UPDATE com COALESCE para campos permitidos
    # Retornar dict com dados atualizados ou None se não encontrado
    pass
