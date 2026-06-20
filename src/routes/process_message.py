import json
import os
from datetime import datetime, date, time
from flask import Blueprint, request
from src.db import get_db_conn
from src.utils.api_response import ok, fail
import src.queries.agendamentos as q_agendamentos
import src.queries.contas as q_contas
from src.routes import helpers
import openai

bp = Blueprint("process_message", __name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@bp.route("/process-message", methods=["POST"])
def process_message():
    """
    POST /process-message
    Endpoint unificado que orquestra todo o fluxo.
    """
    # 1. Validar entrada
    payload = request.get_json()
    if not payload:
        return fail("payload_ausente", "JSON ausente", 400)

    erro_validacao = helpers.validar_entrada(payload)
    if erro_validacao:
        return fail("validacao_falhou", erro_validacao, 400)

    usuario_id = payload.get("usuario_id")
    telefone = payload.get("telefone")
    mensagem = payload.get("mensagem", "").strip()
    session_id = payload.get("session_id")

    # 2. Recuperar contexto do MEI
    try:
        contexto = helpers.recuperar_contexto_mei(usuario_id)
        if not contexto:
            return fail("usuario_nao_encontrado", "Usuário não existe", 404)
    except Exception as e:
        return fail("erro_contexto", str(e), 500)

    # 3. Detectar intenção
    intencao = helpers.detectar_intencao(mensagem, contexto)

    # 4. Verificar se deve coletar contas (momento proativo)
    coletar_contas_agora = helpers.deve_coletar_contas(contexto)

    # Se deve coletar contas E a intenção não é CONTAS, força coleta
    if coletar_contas_agora and intencao != "CONTAS":
        msg_coleta = helpers.construir_mensagem_coleta_contas(contexto)
        resposta_final = helpers.to_json_serializable({
            "resposta": msg_coleta,
            "acao": "COLETAR_CONTAS",
            "intencao": "CONTAS",
            "deve_coletar_contas": True,
            "dados_para_persistir": None,
            "usuario_id": usuario_id,
            "telefone": telefone,
            "session_id": session_id
        })
        return ok(200, resposta_final)

    # 5. Chamar /llm com contexto
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=512,
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": construir_system_prompt_agente5(contexto)
                },
                {
                    "role": "user",
                    "content": mensagem
                }
            ]
        )
        resposta_json = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        return fail("erro_json_resposta", f"IA retornou JSON inválido: {str(e)}", 500)
    except Exception as e:
        return fail("erro_ia", str(e), 500)

    # 6. Extrair campos
    mensagem_resposta = resposta_json.get("mensagem", "")
    acao = resposta_json.get("acao", "RESPONDER")
    dados_persistir = resposta_json.get("dados_para_persistir")

    # 7. Retornar resposta final
    resposta_final = helpers.to_json_serializable({
        "resposta": mensagem_resposta,
        "acao": acao,
        "intencao": intencao,
        "deve_coletar_contas": coletar_contas_agora,
        "dados_para_persistir": dados_persistir,
        "usuario_id": usuario_id,
        "telefone": telefone,
        "session_id": session_id
    })

    return ok(200, resposta_final)


def construir_system_prompt_agente5(contexto: dict) -> str:
    """
    Constrói o system prompt do Agente 5 com contexto completo.
    """
    nome = contexto.get("nome", "MEI")
    cluster = contexto.get("cluster", "freelancer")
    tipo_negocio = contexto.get("tipo_negocio", "negócio")
    onboarding_concluido = contexto.get("onboarding_concluido", False)
    
    agenda = contexto.get("agenda_semana", [])
    contas = contexto.get("contas_fixas", [])

    agenda_text = ""
    if agenda:
        for item in agenda:
            data = item.get("data_compromisso", "")
            hora = item.get("hora_compromisso", "")
            nome_comp = item.get("nome_compromisso", "")
            agenda_text += f"- {data} às {hora}: {nome_comp}\n"
    else:
        agenda_text = "Nenhum compromisso agendado para esta semana."

    contas_text = ""
    if contas:
        for c in contas:
            tipo = c.get("tipo", "")
            valor = c.get("valor", 0)
            dia = c.get("dia_vencimento", "")
            contas_text += f"- {tipo}: R$ {valor:.2f} (dia {dia})\n"
    else:
        contas_text = "Nenhuma conta fixa cadastrada com lembrete ativo."

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
{{
  "mensagem": "sua resposta para o MEI em português natural",
  "acao": "RESPONDER" ou "REGISTRAR_AGENDAMENTO",
  "dados_para_persistir": null ou {{
    "nome_compromisso": "nome do compromisso",
    "data_compromisso": "YYYY-MM-DD",
    "hora_compromisso": "HH:MM"
  }}
}}

NUNCA inclua texto fora do JSON.
"""
    return prompt


@bp.route("/process-message/debug", methods=["GET"])
def debug_process_message():
    """
    GET /process-message/debug?usuario_id=40
    Retorna contexto completo sem chamar IA.
    """
    usuario_id = request.args.get("usuario_id", type=int)
    if not usuario_id:
        return fail("usuario_id_obrigatorio", "usuario_id é obrigatório", 400)

    try:
        contexto = helpers.recuperar_contexto_mei(usuario_id)
        if not contexto:
            return fail("usuario_nao_encontrado", "Usuário não existe", 404)

        coletar = helpers.deve_coletar_contas(contexto)

        debug_data = helpers.to_json_serializable({
            "contexto": contexto,
            "deve_coletar_contas": coletar,
            "mensagem_coleta": helpers.construir_mensagem_coleta_contas(contexto) if coletar else None
        })

        return ok(200, debug_data)
    except Exception as e:
        return fail("erro_debug", str(e), 500)
