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
            cluster, onboarding_step, confirmacao_lembretes, onboarding_concluido,
            perfil_tipo, eh_mei, profissao, modalidade,
            conselho_sigla, conselho_uf, conselho_numero,
            uf, municipio, followup_agendado, followup_timestamp
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
            perfil_tipo             = COALESCE(%(perfil_tipo)s, perfil_tipo),
            eh_mei                  = COALESCE(%(eh_mei)s, eh_mei),
            profissao               = COALESCE(%(profissao)s, profissao),
            modalidade              = COALESCE(%(modalidade)s, modalidade),
            conselho_sigla          = COALESCE(%(conselho_sigla)s, conselho_sigla),
            conselho_uf             = COALESCE(%(conselho_uf)s, conselho_uf),
            conselho_numero         = COALESCE(%(conselho_numero)s, conselho_numero),
            uf                      = COALESCE(%(uf)s, uf),
            municipio               = COALESCE(%(municipio)s, municipio),
            followup_agendado       = COALESCE(%(followup_agendado)s, followup_agendado),
            followup_timestamp      = COALESCE(%(followup_timestamp)s, followup_timestamp),
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
        "perfil_tipo": None,
        "eh_mei": None,
        "profissao": None,
        "modalidade": None,
        "conselho_sigla": None,
        "conselho_uf": None,
        "conselho_numero": None,
        "uf": None,
        "municipio": None,
        "followup_agendado": None,
        "followup_timestamp": None,
    }
    params.update(fields)

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None


def reset_demo(conn, usuario_id: int) -> dict | None:
    """Zera onboarding do usuário pra disparar o fluxo de novo (demo replay).

    Mantém o cadastro (id, numero_telefone) e todo dado de negócio intacto —
    agenda, contas recorrentes, lista de compras e comprovantes (gastos/vendas)
    não são apagados. Só limpa `feedbacks` e `chat_memory` pra o bot não
    "lembrar" da conversa/feedback anterior no replay do onboarding.
    """
    sql_update = """
        UPDATE public.usuarios
        SET
            estado_atual          = 'menu',
            interacao_previa      = false,
            onboarding_step       = NULL,
            onboarding_concluido  = false,
            onboarding_timestamp  = NULL,
            tipo_negocio          = NULL,
            descricao_negocio     = NULL,
            descricao_objetivo    = NULL,
            area_ajuda            = NULL,
            preco_referencia      = NULL,
            dias_trabalho         = NULL,
            horario_inicio        = NULL,
            horario_fim           = NULL,
            contas_fixas_completo = false,
            perfil_tipo           = NULL,
            eh_mei                = NULL,
            profissao             = NULL,
            modalidade            = NULL,
            conselho_sigla        = NULL,
            conselho_uf           = NULL,
            conselho_numero       = NULL,
            uf                    = NULL,
            municipio             = NULL,
            followup_agendado     = false,
            followup_timestamp    = NULL
        WHERE id = %(usuario_id)s
        RETURNING *;
    """

    sql_deletes = [
        "DELETE FROM public.feedbacks WHERE usuario_id = %(usuario_id)s;",
        "DELETE FROM public.chat_memory WHERE usuario_id = %(usuario_id)s;",
        "DELETE FROM public.preferencias_notificacao WHERE usuario_id = %(usuario_id)s;",
    ]

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql_update, {"usuario_id": usuario_id})
        row = cursor.fetchone()
        if not row:
            return None

        for sql in sql_deletes:
            cursor.execute(sql, {"usuario_id": usuario_id})

        return dict(row)


# Tipos válidos de preferência de notificação (espelha o CHECK da tabela).
NOTIF_TIPOS = (
    "das", "declaracao", "inss", "carneleao", "ir", "irpf",
    "tff_iss", "segunda", "relatorio", "lembrete_relatorio",
)


def get_notificacoes(conn, usuario_id: int) -> list:
    """Retorna as preferências de notificação do usuário (1 linha por tipo)."""
    sql = """
        SELECT tipo, ativo
        FROM public.preferencias_notificacao
        WHERE usuario_id = %(usuario_id)s
        ORDER BY tipo;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"usuario_id": usuario_id})
        return [dict(row) for row in cursor.fetchall()]


def upsert_notificacoes(conn, usuario_id: int, prefs: dict) -> list:
    """Upsert idempotente de preferências: {tipo: ativo(bool)}.

    Insere ou atualiza uma linha por (usuario_id, tipo); só toca os tipos
    informados. Retorna o conjunto completo atual do usuário.
    """
    sql = """
        INSERT INTO public.preferencias_notificacao (usuario_id, tipo, ativo)
        VALUES (%(usuario_id)s, %(tipo)s, %(ativo)s)
        ON CONFLICT (usuario_id, tipo)
        DO UPDATE SET ativo = EXCLUDED.ativo, updated_at = NOW();
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        for tipo, ativo in prefs.items():
            cursor.execute(
                sql,
                {"usuario_id": usuario_id, "tipo": tipo, "ativo": bool(ativo)},
            )
    return get_notificacoes(conn, usuario_id)


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



def find_telefones_by_ids(conn, usuario_ids: list) -> dict:
    """Resolve {id: numero_telefone} para os ids informados, numa query só.

    Existe para a invalidação de cache: a chave do L2 é `user:<telefone>`, mas
    escrita externa (SQL manual, job) identifica o usuário por id. Ids ausentes
    simplesmente não aparecem no dict — o caller reporta como não-encontrados.
    """
    if not usuario_ids:
        return {}

    sql = """
        SELECT id, numero_telefone
        FROM public.usuarios
        WHERE id = ANY(%(ids)s);
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(sql, {"ids": list(usuario_ids)})
        return {row["id"]: row["numero_telefone"] for row in cursor.fetchall()}
