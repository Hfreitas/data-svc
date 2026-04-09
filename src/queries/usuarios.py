"""
Queries de usuários — funções puras que recebem conn + parâmetros e retornam rows.
Nenhuma lógica HTTP ou de cache aqui.
"""
from psycopg2.extras import RealDictCursor


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
    sql = """
        WITH existing_user AS (
        SELECT * FROM public.usuarios
        WHERE numero_telefone = %(numero_telefone)s
        ),
        inserted_user AS (
        INSERT INTO public.usuarios (
            numero_telefone, nome, razao_social,
            interacao_previa, data_primeiro_contato, data_ultimo_contato, estado_atual)
        SELECT
            %(numero_telefone)s, %(nome)s, %(razao_social)s,
            false, NOW(), CURRENT_DATE, 'menu'
        WHERE NOT EXISTS (SELECT 1 FROM existing_user)
        RETURNING *
        )
        SELECT * FROM existing_user
        UNION ALL SELECT * FROM inserted_user;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            sql, 
            {
                "numero_telefone": numero_telefone, 
                "nome": nome, 
                "razao_social": razao_social},
        )

        row = cursor.fetchone()
        
        return dict(row)
        
    


def update(conn, usuario_id: int, fields: dict) -> dict | None:
    # TODO: implementar
    # Executar UPDATE com COALESCE para campos permitidos
    # Retornar dict com dados atualizados ou None se não encontrado
    sql = """
        UPDATE public.usuarios
        SET
            nome                = COALESCE(%(nome)s, nome),
            razao_social        = COALESCE(%(razao_social)s, razao_social),
            estado_atual        = COALESCE(%(estado_atual)s, estado_atual),
            interacao_previa    = COALESCE(%(interacao_previa)s, interacao_previa),
            tipo_negocio        = COALESCE(%(tipo_negocio)s, tipo_negocio),
            descricao_negocio   = COALESCE(%(descricao_negocio)s, descricao_negocio),
            descricao_objetivo  = COALESCE(%(descricao_objetivo)s, descricao_objetivo),
            area_ajuda          = COALESCE(%(area_ajuda)s, area_ajuda),
            preco_referencia    = COALESCE(%(preco_referencia)s, preco_referencia),
            dias_trabalho       = COALESCE(%(dias_trabalho)s, dias_trabalho),
            horario_inicio      = COALESCE(%(horario_inicio)s, horario_inicio),
            horario_fim         = COALESCE(%(horario_fim)s, horario_fim),
            data_ultimo_contato = NOW()
        WHERE id = %(id)s
        RETURNING *;
    """
    
    params = {
        "id": usuario_id,
        "nome": None,
        "razao_social": None,
        "estado_atual": None,
        "interacao_previa": None,
        "tipo_negocio": None,
        "descricao_negocio": None,
        "descricao_objetivo": None,
        "area_ajuda": None,
        "preco_referencia": None,
        "dias_trabalho": None,
        "horario_inicio": None,
        "horario_fim": None,
    }
    params.update(fields)

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
