"""
Queries de usuários — funções puras que recebem conn + parâmetros e retornam rows.
Nenhuma lógica HTTP ou de cache aqui.
"""
from psycopg2.extras import RealDictCursor


def find_by_telefone(conn, telefone: str) -> dict | None:
    sql = """
        SELECT
            id, numero_telefone, nome, razao_social, email,
            estado_atual, interacao_previa,
            tipo_negocio, descricao_negocio, descricao_objetivo,
            area_ajuda, preco_referencia,
            dias_trabalho, horario_inicio, horario_fim,
            data_primeiro_contato, data_ultimo_contato,
            versao_agente, cpf_cnpj,
            cluster, onboarding_step, confirmacao_lembretes, onboarding_concluido
        FROM public.usuarios
        WHERE numero_telefone = %(telefone)s
        LIMIT 1;
    """
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"telefone": telefone})
        row = cursor.fetchone()
        return dict(row) if row else None
    


def upsert(conn, numero_telefone: str, nome: str, razao_social: str) -> dict:
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
    sql = """
        UPDATE public.usuarios
        SET
            nome                    = COALESCE(%(nome)s, nome),
            razao_social            = COALESCE(%(razao_social)s, razao_social),
            estado_atual            = COALESCE(%(estado_atual)s, estado_atual),
            interacao_previa        = COALESCE(%(interacao_previa)s, interacao_previa),
            tipo_negocio            = COALESCE(%(tipo_negocio)s, tipo_negocio),
            descricao_negocio       = COALESCE(%(descricao_negocio)s, descricao_negocio),
            descricao_objetivo      = COALESCE(%(descricao_objetivo)s, descricao_objetivo),
            area_ajuda              = COALESCE(%(area_ajuda)s, area_ajuda),
            preco_referencia        = COALESCE(%(preco_referencia)s, preco_referencia),
            dias_trabalho           = COALESCE(%(dias_trabalho)s, dias_trabalho),
            horario_inicio          = COALESCE(%(horario_inicio)s, horario_inicio),
            horario_fim             = COALESCE(%(horario_fim)s, horario_fim),
            versao_agente           = COALESCE(%(versao_agente)s, versao_agente),
            confirmacao_lembretes   = COALESCE(%(confirmacao_lembretes)s, confirmacao_lembretes),
            cluster                 = COALESCE(%(cluster)s, cluster),
            onboarding_step         = COALESCE(%(onboarding_step)s, onboarding_step),
            onboarding_concluido    = COALESCE(%(onboarding_concluido)s, onboarding_concluido),
            onboarding_timestamp    = COALESCE(%(onboarding_timestamp)s, onboarding_timestamp),
            contas_fixas_completo   = COALESCE(%(contas_fixas_completo)s, contas_fixas_completo),
            ultimo_relatorio        = COALESCE(%(ultimo_relatorio)s, ultimo_relatorio),
            cpf_cnpj                = COALESCE(%(cpf_cnpj)s, cpf_cnpj),
            data_ultimo_contato     = NOW()
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
        "versao_agente": None,
        "confirmacao_lembretes": None,
        "cluster": None,
        "onboarding_step": None,
        "onboarding_concluido": None,
        "onboarding_timestamp": None,
        "contas_fixas_completo": None,
        "ultimo_relatorio": None,
        "cpf_cnpj": None,
    }
    params.update(fields)

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_prox_nfe(conn, usuario_id: int) -> dict:
    sql = """
        SELECT COALESCE(MAX(nfe_number), 0) + 1 AS prox
        FROM public.invoice
        WHERE user_id = %(usuario_id)s;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        row = cursor.fetchone()
        prox = row["prox"] if row else 1
        return {"nfeNumber": prox, "rpsNumber": prox}


def get_clientes_nf(conn, usuario_id: int) -> list:
    sql = """
        SELECT e.id, e.name AS nome, e.federal_tax_number AS cnpj, e.email
        FROM public.enterprise_user eu
        JOIN public.enterprise e ON eu.id_enterprise = e.id
        WHERE eu.id_user = %(usuario_id)s
        ORDER BY e.name;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def save_cliente_nf(conn, usuario_id: int, nome: str, cnpj: str, email: str) -> dict:
    sql_upsert_enterprise = """
        INSERT INTO public.enterprise (name, legal_name, federal_tax_number, email)
        VALUES (%(nome)s, %(nome)s, %(cnpj)s, %(email)s)
        ON CONFLICT (federal_tax_number)
        DO UPDATE SET name = %(nome)s, legal_name = %(nome)s, email = %(email)s
        RETURNING id;
    """
    sql_check_link = """
        SELECT id FROM public.enterprise_user
        WHERE id_user = %(id_user)s AND id_enterprise = %(id_enterprise)s
        LIMIT 1;
    """
    sql_link_user = """
        INSERT INTO public.enterprise_user (id_user, id_enterprise)
        VALUES (%(id_user)s, %(id_enterprise)s);
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql_upsert_enterprise, {"nome": nome, "cnpj": cnpj, "email": email})
        ent_row = cursor.fetchone()
        enterprise_id = ent_row["id"]

        cursor.execute(sql_check_link, {"id_user": usuario_id, "id_enterprise": enterprise_id})
        if not cursor.fetchone():
            cursor.execute(sql_link_user, {"id_user": usuario_id, "id_enterprise": enterprise_id})

    return {"id": enterprise_id, "nome": nome, "cnpj": cnpj, "email": email}

