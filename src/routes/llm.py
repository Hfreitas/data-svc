import json
import os
from datetime import datetime, date, time
from flask import Blueprint, request
from src.db import get_db_conn
from src.utils.api_response import ok, fail
import src.queries.agendamentos as q_agendamentos
import src.queries.contas as q_contas
import openai

bp = Blueprint("llm", __name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ========== Serialização JSON-Safe ==========

def to_json_serializable(obj):
    """Converte objetos complexos para strings ISO."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.strftime("%H:%M:%S")
    if isinstance(obj, dict):
        return {k: to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_json_serializable(item) for item in obj]
    return str(obj)


# ========== Recuperação de Dados ==========

def recuperar_perfil(usuario_id: int) -> dict | None:
    """Busca dados do usuário do banco."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, nome, tipo_negocio, cluster, onboarding_concluido
                FROM usuarios
                WHERE id = %s
            """, (usuario_id,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "nome": row[1],
                "tipo_negocio": row[2],
                "cluster": row[3],
                "onboarding_concluido": row[4]
            }


def recuperar_historico_24h(usuario_id: int, limit: int = 20) -> list[dict]:
    """Busca histórico de chat das últimas 24h."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT papel, conteudo, criado_em
                FROM chat_memory
                WHERE usuario_id = %s
                  AND criado_em >= NOW() - INTERVAL '24 hours'
                ORDER BY criado_em ASC
                LIMIT %s
            """, (usuario_id, limit))
            rows = cur.fetchall()
            return [
                {"role": r[0], "content": r[1], "criado_em": r[2].isoformat()}
                for r in rows
            ]


def recuperar_agenda_semana(usuario_id: int) -> list[dict]:
    """Busca compromissos da semana usando a query existente."""
    with get_db_conn() as conn:
        return q_agendamentos.list_semana(conn, usuario_id)


def recuperar_contas_fixas(usuario_id: int) -> list[dict]:
    """Busca contas fixas ativas do usuário."""
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tipo, descricao, valor, dia_vencimento
                FROM contas_recorrentes
                WHERE usuario_id = %s AND lembrete_ativo = true
                ORDER BY dia_vencimento
            """, (usuario_id,))
            rows = cur.fetchall()
            return [
                {
                    "tipo": r[0],
                    "descricao": r[1],
                    "valor": float(r[2]),
                    "dia_vencimento": r[3]
                }
                for r in rows
            ]


# ========== Construção do Prompt ==========

def construir_system_prompt(perfil: dict, historico: list, agenda: list, contas: list) -> str:
    """Monta o system prompt do Agente 5 com contexto completo."""

    nome = perfil.get("nome", "MEI") if perfil else "MEI"
    cluster = perfil.get("cluster", "freelancer") if perfil else "freelancer"
    tipo_negocio = perfil.get("tipo_negocio", "negócio") if perfil else "negócio"
    onboarding_concluido = perfil.get("onboarding_concluido", False) if perfil else False

    # Monta agenda da semana
    agenda_text = ""
    if agenda:
        for item in agenda:
            data = item.get("data_compromisso", "")
            hora = item.get("hora_compromisso", "")
            nome_comp = item.get("nome_compromisso", "")
            agenda_text += f"- {data} às {hora}: {nome_comp}\n"
    else:
        agenda_text = "Nenhum compromisso agendado para esta semana."

    # Monta contas fixas
    contas_text = ""
    if contas:
        for c in contas:
            tipo = c.get("tipo", "")
            valor = c.get("valor", 0)
            dia = c.get("dia_vencimento", "")
            contas_text += f"- {tipo}: R$ {valor:.2f} (dia {dia})\n"
    else:
        contas_text = "Nenhuma conta fixa cadastrada com lembrete ativo."

    # Data e dia da semana
    agora = datetime.now()
    data_atual = agora.strftime("%d/%m/%Y")
    
    dia_names = {
        "Monday": "segunda-feira",
        "Tuesday": "terça-feira",
        "Wednesday": "quarta-feira",
        "Thursday": "quinta-feira",
        "Friday": "sexta-feira",
        "Saturday": "sábado",
        "Sunday": "domingo"
    }
    dia_semana = dia_names.get(agora.strftime("%A"), agora.strftime("%A"))

    prompt = f"""Você é MEIrelles, a secretária do MEI no WhatsApp.

**SEU PAPEL:**
- Organizar compromissos e lembretes
- Gerenciar a rotina de trabalho
- Coletar contas fixas mensais
- Responder perguntas sobre agenda e contas

**DADOS DO MEI:**
- Nome: {nome}
- Tipo de negócio: {tipo_negocio}
- Cluster: {cluster}
- Onboarding completo? {'Sim' if onboarding_concluido else 'Não'}

**AGENDA DESTA SEMANA ({data_atual} - {dia_semana}):**
{agenda_text}

**CONTAS FIXAS CADASTRADAS:**
{contas_text}

**REGRAS CRÍTICAS:**
1. NUNCA registre compromissos sem confirmação explícita do MEI
2. Sempre mostre resumo antes de salvar
3. Para agendar, exija: nome, data e hora
4. Se o horário já está ocupado, sugira alternativas
5. Seu tom é direto, eficiente — o MEI está trabalhando

**RESPOSTA EM JSON (OBRIGATÓRIO):**
Sua resposta DEVE ser um JSON válido com esta estrutura:
{{
  "mensagem": "sua resposta para o MEI em português natural",
  "acao": "RESPONDER" ou "REGISTRAR_AGENDAMENTO",
  "dados_para_persistir": null ou {{
    "nome_compromisso": "nome do compromisso",
    "data_compromisso": "YYYY-MM-DD",
    "hora_compromisso": "HH:MM"
  }}
}}

REGRA: Use "REGISTRAR_AGENDAMENTO" APENAS quando o MEI confirmar explicitamente (responder "1", "sim", "confirma", etc).
NUNCA inclua texto fora do JSON.
"""
    return prompt


# ========== Endpoint Principal ==========

@bp.route("/llm", methods=["POST"])
def gerar_resposta():
    """
    POST /llm
    Processa mensagem do MEI através da IA e retorna resposta + ação.
    """
    payload = request.get_json()
    if not payload:
        return fail("payload_ausente", "JSON ausente", 400)

    usuario_id = payload.get("usuario_id")
    telefone = payload.get("telefone")
    mensagem = payload.get("mensagem", "").strip()
    session_id = payload.get("session_id")

    if not usuario_id or not mensagem:
        return fail("campos_faltando", "usuario_id e mensagem são obrigatórios", 400)

    # Recupera dados do MEI
    perfil = recuperar_perfil(usuario_id)
    if not perfil:
        return fail("usuario_nao_encontrado", "Usuário não existe", 404)

    historico = recuperar_historico_24h(usuario_id)
    agenda = recuperar_agenda_semana(usuario_id)
    contas = recuperar_contas_fixas(usuario_id)

    # Monta prompt com contexto completo
    system_prompt = construir_system_prompt(perfil, historico, agenda, contas)

    # Prepara mensagens para OpenAI
    messages = [
        {"role": "system", "content": system_prompt}
    ]

    # Adiciona histórico (últimas 20 mensagens)
    for h in historico[-20:]:
        messages.append({"role": h["role"], "content": h["content"]})

    # Adiciona mensagem atual do MEI
    messages.append({"role": "user", "content": mensagem})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=512,
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=messages
        )
        resposta_json = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        return fail("erro_json_resposta", f"IA retornou JSON inválido: {str(e)}", 500)
    except Exception as e:
        return fail("erro_ia", str(e), 500)

    # Extrai campos da resposta
    mensagem_resposta = resposta_json.get("mensagem", "")
    acao = resposta_json.get("acao", "RESPONDER")
    dados_persistir = resposta_json.get("dados_para_persistir")

    # Serializa para JSON-safe (converte dates → ISO, etc)
    resposta_final = to_json_serializable({
        "resposta": mensagem_resposta,
        "acao": acao,
        "dados_para_persistir": dados_persistir,
        "usuario_id": usuario_id,
        "telefone": telefone,
        "session_id": session_id
    })

    return ok(200, resposta_final)


# ========== Endpoints Auxiliares ==========

@bp.route("/llm/debug", methods=["GET"])
def debug_contexto():
    """
    GET /llm/debug?usuario_id=40
    Retorna o contexto completo sem chamar a IA (útil para debug).
    """
    usuario_id = request.args.get("usuario_id", type=int)
    if not usuario_id:
        return fail("usuario_id_obrigatorio", "Query param 'usuario_id' é obrigatório", 400)

    perfil = recuperar_perfil(usuario_id)
    if not perfil:
        return fail("usuario_nao_encontrado", "Usuário não existe", 404)

    historico = recuperar_historico_24h(usuario_id)
    agenda = recuperar_agenda_semana(usuario_id)
    contas = recuperar_contas_fixas(usuario_id)

    debug_data = to_json_serializable({
        "perfil": perfil,
        "historico": historico,
        "agenda": agenda,
        "contas": contas,
        "system_prompt": construir_system_prompt(perfil, historico, agenda, contas)
    })

    return ok(200, debug_data)


@bp.route("/llm/prompt-test", methods=["POST"])
def prompt_test():
    """
    POST /llm/prompt-test
    Testa a construção do prompt sem chamar OpenAI (economiza créditos).
    """
    payload = request.get_json()
    if not payload or "usuario_id" not in payload:
        return fail("usuario_id_obrigatorio", "usuario_id é obrigatório", 400)

    usuario_id = payload["usuario_id"]
    perfil = recuperar_perfil(usuario_id)
    if not perfil:
        return fail("usuario_nao_encontrado", "Usuário não existe", 404)

    historico = recuperar_historico_24h(usuario_id)
    agenda = recuperar_agenda_semana(usuario_id)
    contas = recuperar_contas_fixas(usuario_id)

    system_prompt = construir_system_prompt(perfil, historico, agenda, contas)

    return ok(200, to_json_serializable({"system_prompt": system_prompt}))
