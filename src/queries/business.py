"""
Queries do Agente Business — funções puras que recebem conn + parâmetros e retornam rows.
Nenhuma lógica HTTP ou de cache aqui.
"""
from psycopg2.extras import RealDictCursor


def get_contexto_usuario(conn, usuario_id: int) -> dict | None:
    """Retorna perfil do usuário + campos computados: descricao_completa, proximo_campo_fila, status_trial."""
    sql = """
        SELECT
            u.id,
            u.nome,
            u.razao_social,
            u.tipo_negocio,
            u.descricao_negocio,
            u.descricao_objetivo,
            u.data_primeiro_contato,
            u.ultimo_relatorio,
            u.confirmacao_lembretes,
            u.interacao_previa,
            (
                u.descricao_negocio IS NOT NULL AND u.descricao_negocio <> ''
                AND u.descricao_objetivo IS NOT NULL AND u.descricao_objetivo <> ''
            ) AS descricao_completa,
            CASE
                WHEN u.nome IS NULL OR u.nome = ''           THEN 'nome_mei'
                WHEN u.tipo_negocio IS NULL                  THEN 'cluster'
                WHEN u.razao_social IS NULL                  THEN 'nome_negocio'
                WHEN NOT u.confirmacao_lembretes             THEN 'confirmacao_lembretes'
                WHEN u.descricao_negocio IS NULL OR u.descricao_negocio = '' THEN 'descricao_negocio'
                ELSE NULL
            END AS proximo_campo_fila,
            -- status_trial derivado de assinaturas
            CASE
                WHEN EXISTS (
                    SELECT 1 FROM public.assinaturas a
                    WHERE a.usuario_id = u.id AND a.active = true
                ) THEN 'ativo'
                WHEN EXISTS (
                    SELECT 1 FROM public.assinaturas a
                    WHERE a.usuario_id = u.id AND a.active = false
                ) THEN 'encerrado'
                ELSE 'trial'
            END AS status_trial
        FROM public.usuarios u
        WHERE u.id = %(usuario_id)s;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        row = cur.fetchone()
        return dict(row) if row else None


def get_registros_semana(conn, usuario_id: int) -> dict:
    """Agrega comprovantes dos últimos 7 dias: contagem, total_vendas, total_gastos, saldo."""
    sql = """
        SELECT
            COUNT(*)::int AS contagem,
            COALESCE(SUM(CASE WHEN operacao = 'venda' THEN valor_total END), 0)::float AS total_vendas,
            COALESCE(SUM(CASE WHEN operacao = 'gasto' THEN valor_total END), 0)::float AS total_gastos,
            (
                COALESCE(SUM(CASE WHEN operacao = 'venda' THEN valor_total END), 0)
                - COALESCE(SUM(CASE WHEN operacao = 'gasto' THEN valor_total END), 0)
            )::float AS saldo
        FROM public.comprovantes
        WHERE usuario_id = %(usuario_id)s
          AND (
              (operacao = 'venda' AND data_venda >= CURRENT_DATE - INTERVAL '7 days'
                                  AND data_venda <= CURRENT_DATE)
           OR (operacao = 'gasto' AND data_compra >= CURRENT_DATE - INTERVAL '7 days'
                                  AND data_compra <= CURRENT_DATE)
          );
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        row = cur.fetchone()
        return dict(row) if row else {"contagem": 0, "total_vendas": 0.0, "total_gastos": 0.0, "saldo": 0.0}


def get_registros_mes(conn, usuario_id: int) -> dict:
    """Agrega comprovantes do mês corrente: contagem, total_vendas, total_gastos, saldo."""
    sql = """
        SELECT
            COUNT(*)::int AS contagem,
            COALESCE(SUM(CASE WHEN operacao = 'venda' THEN valor_total END), 0)::float AS total_vendas,
            COALESCE(SUM(CASE WHEN operacao = 'gasto' THEN valor_total END), 0)::float AS total_gastos,
            (
                COALESCE(SUM(CASE WHEN operacao = 'venda' THEN valor_total END), 0)
                - COALESCE(SUM(CASE WHEN operacao = 'gasto' THEN valor_total END), 0)
            )::float AS saldo
        FROM public.comprovantes
        WHERE usuario_id = %(usuario_id)s
          AND (
              (operacao = 'venda' AND data_venda >= date_trunc('month', CURRENT_DATE)
                                  AND data_venda < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month')
           OR (operacao = 'gasto' AND data_compra >= date_trunc('month', CURRENT_DATE)
                                  AND data_compra < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month')
          );
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        row = cur.fetchone()
        return dict(row) if row else {"contagem": 0, "total_vendas": 0.0, "total_gastos": 0.0, "saldo": 0.0}


def get_historico_meses(conn, usuario_id: int) -> list:
    """Retorna totais mensais dos 3 meses completos anteriores ao mês atual."""
    sql = """
        SELECT
            EXTRACT(YEAR  FROM eff_date)::int AS ano,
            EXTRACT(MONTH FROM eff_date)::int AS mes,
            COALESCE(SUM(CASE WHEN operacao = 'venda' THEN valor_total END), 0)::float AS total_vendas,
            COALESCE(SUM(CASE WHEN operacao = 'gasto' THEN valor_total END), 0)::float AS total_gastos
        FROM (
            SELECT operacao, valor_total, data_venda AS eff_date
            FROM public.comprovantes
            WHERE usuario_id = %(usuario_id)s AND operacao = 'venda' AND data_venda IS NOT NULL
            UNION ALL
            SELECT operacao, valor_total, data_compra AS eff_date
            FROM public.comprovantes
            WHERE usuario_id = %(usuario_id)s AND operacao = 'gasto' AND data_compra IS NOT NULL
        ) src
        WHERE eff_date >= date_trunc('month', CURRENT_DATE) - INTERVAL '3 months'
          AND eff_date <  date_trunc('month', CURRENT_DATE)
        GROUP BY ano, mes
        ORDER BY ano, mes;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        return [dict(r) for r in cur.fetchall()]


def get_faturamento_acumulado_ano(conn, usuario_id: int) -> float:
    """Soma todas as vendas do ano corrente — base para acompanhar limite DASN-SIMEI (R$ 81k)."""
    sql = """
        SELECT COALESCE(SUM(valor_total), 0)::float AS total
        FROM public.comprovantes
        WHERE usuario_id = %(usuario_id)s
          AND operacao = 'venda'
          AND data_venda >= date_trunc('year', CURRENT_DATE)
          AND data_venda <  date_trunc('year', CURRENT_DATE) + INTERVAL '1 year';
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        row = cur.fetchone()
        return float(row["total"]) if row else 0.0


def get_gastos_recorrentes(conn, usuario_id: int) -> list:
    """
    Merge de duas fontes:
    1. Comprovantes ad-hoc com mesmo item em 2+ dos últimos 3 meses completos
    2. Contas recorrentes cadastradas (ativo=true)
    Deduplicado por nome normalizado (LOWER/TRIM).
    """
    sql = """
        WITH ad_hoc AS (
            SELECT
                LOWER(TRIM(item)) AS item_norm,
                COUNT(DISTINCT EXTRACT(MONTH FROM data_compra))::int AS meses,
                AVG(valor_total)::float AS valor_medio
            FROM public.comprovantes
            WHERE usuario_id = %(usuario_id)s
              AND operacao = 'gasto'
              AND data_compra >= date_trunc('month', CURRENT_DATE) - INTERVAL '3 months'
              AND data_compra <  date_trunc('month', CURRENT_DATE)
              AND item IS NOT NULL AND item <> ''
            GROUP BY item_norm
            HAVING COUNT(DISTINCT EXTRACT(MONTH FROM data_compra)) >= 2
        ),
        estruturadas AS (
            SELECT
                LOWER(TRIM(COALESCE(descricao, tipo))) AS item_norm,
                3 AS meses,
                valor::float AS valor_medio
            FROM public.contas_recorrentes
            WHERE usuario_id = %(usuario_id)s AND ativo = true
        ),
        merged AS (
            SELECT item_norm, meses, valor_medio FROM ad_hoc
            UNION
            SELECT item_norm, meses, valor_medio FROM estruturadas
        )
        SELECT item_norm AS item, meses AS meses_consecutivos, ROUND(valor_medio::numeric, 2)::float AS valor
        FROM merged
        ORDER BY valor DESC;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        return [dict(r) for r in cur.fetchall()]


def insert_meicheck_log(conn, data: dict) -> dict:
    """Persiste log de execução do Agente Business na tabela meicheck_logs."""
    sql = """
        INSERT INTO public.meicheck_logs (
            request_id, usuario_id, nome, tipo_negocio, razao_social,
            numero_profissional, data_validation_score, data_gaps,
            integrity_score, has_critical_gaps, contexto,
            ia_response_text, ia_word_count, ia_validation_score, ia_validation_percent,
            can_persist, adaptation_score, cluster_category, cluster_weight,
            is_seasonal_now, channel, trigger_type, status
        ) VALUES (
            %(request_id)s, %(usuario_id)s, %(nome)s, %(tipo_negocio)s, %(razao_social)s,
            %(numero_profissional)s, %(data_validation_score)s, %(data_gaps)s,
            %(integrity_score)s, %(has_critical_gaps)s, %(contexto)s,
            %(ia_response_text)s, %(ia_word_count)s, %(ia_validation_score)s, %(ia_validation_percent)s,
            %(can_persist)s, %(adaptation_score)s, %(cluster_category)s, %(cluster_weight)s,
            %(is_seasonal_now)s, %(channel)s, %(trigger_type)s, %(status)s
        )
        RETURNING id, request_id, created_at;
    """
    import json as _json
    params = {
        "request_id": data.get("request_id") or "",
        "usuario_id": str(data.get("usuario_id", "")),
        "nome": data.get("nome"),
        "tipo_negocio": data.get("tipo_negocio"),
        "razao_social": data.get("razao_social"),
        "numero_profissional": data.get("numero_profissional"),
        "data_validation_score": data.get("data_validation_score", 0),
        "data_gaps": _json.dumps(data.get("data_gaps")) if data.get("data_gaps") is not None else None,
        "integrity_score": data.get("integrity_score", 0),
        "has_critical_gaps": data.get("has_critical_gaps", False),
        "contexto": _json.dumps(data.get("contexto")) if data.get("contexto") is not None else None,
        "ia_response_text": data.get("ia_response_text"),
        "ia_word_count": data.get("ia_word_count"),
        "ia_validation_score": data.get("ia_validation_score", 0),
        "ia_validation_percent": data.get("ia_validation_percent", 0),
        "can_persist": data.get("can_persist", False),
        "adaptation_score": data.get("adaptation_score", 0),
        "cluster_category": data.get("cluster_category"),
        "cluster_weight": data.get("cluster_weight"),
        "is_seasonal_now": data.get("is_seasonal_now", False),
        "channel": data.get("channel", "whatsapp"),
        "trigger_type": data.get("trigger_type", "webhook"),
        "status": data.get("status", "completed"),
    }
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row)


def list_contas_recorrentes(conn, usuario_id: int) -> list:
    """Lista contas recorrentes ativas do usuário (ativo=true)."""
    sql = """
        SELECT id, tipo, descricao, valor, dia_vencimento, lembrete_ativo, ativo, created_at
        FROM public.contas_recorrentes
        WHERE usuario_id = %(usuario_id)s AND ativo = true
        ORDER BY tipo, descricao;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"usuario_id": usuario_id})
        return [dict(r) for r in cur.fetchall()]
