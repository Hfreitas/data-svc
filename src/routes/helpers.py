"""Helpers para /process-message"""
from datetime import datetime, date, time
import re
from src.db import get_db_conn
import src.queries.agendamentos as q_agendamentos
import src.queries.contas as q_contas


def to_json_serializable(obj):
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


def validar_entrada(payload: dict) -> str | None:
    if not payload.get("usuario_id"):
        return "usuario_id obrigatório"
    if not payload.get("telefone"):
        return "telefone obrigatório"
    if not payload.get("mensagem"):
        return "mensagem obrigatória"
    return None


def recuperar_contexto_mei(usuario_id: int) -> dict | None:
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nome, tipo_negocio, cluster, onboarding_concluido FROM usuarios WHERE id = %s",
                (usuario_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            perfil = {
                "id": row[0],
                "nome": row[1],
                "tipo_negocio": row[2],
                "cluster": row[3],
                "onboarding_concluido": row[4],
            }
        agenda = q_agendamentos.list_semana(conn, usuario_id)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tipo, descricao, valor, dia_vencimento FROM contas_recorrentes WHERE usuario_id = %s AND lembrete_ativo = true",
                (usuario_id,),
            )
            contas = [
                {
                    "tipo": r[0],
                    "descricao": r[1],
                    "valor": float(r[2]),
                    "dia_vencimento": r[3],
                }
                for r in cur.fetchall()
            ]
        return {"perfil": perfil, "agenda_semana": agenda, "contas_fixas": contas, **perfil}


def detectar_intencao(mensagem: str, contexto: dict) -> str:
    msg = mensagem.lower()
    if any(p in msg for p in ["agendar", "marcar", "reunião", "reuniao", "compromisso"]):
        return "AGENDA"
    if any(p in msg for p in ["conta", "pagar", "boleto", "vencimento"]):
        return "CONTAS"
    if any(p in msg for p in ["quanto", "qual", "quando", "como"]):
        return "CONSULTA"
    return "GERAL"


def deve_coletar_contas(contexto: dict) -> bool:
    return False


def construir_mensagem_coleta_contas(contexto: dict) -> str:
    return ""
