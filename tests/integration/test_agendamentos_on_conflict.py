"""Integração real: ON CONFLICT unique_agendamento_por_usuario.

Roda só com Postgres acessível (DATABASE_URL). Skip automático em CI unitário.

  DATABASE_URL=... .venv/bin/pytest tests/integration/test_agendamentos_on_conflict.py -q
  # ou via container local:
  docker exec -e PYTHONPATH=/app -w /app dev-data-svc-1 \
    python3 -c '...'  # ver scripts abaixo / smoke
"""
from __future__ import annotations

import os
import uuid
from datetime import date, timedelta

import psycopg2
import pytest
from psycopg2.extras import RealDictCursor

import src.queries.agendamentos as q


def _can_connect(dsn: str) -> bool:
    try:
        conn = psycopg2.connect(dsn, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


DSN = os.environ.get("DATABASE_URL") or os.environ.get("DATA_SVC_DATABASE_URL") or ""
pytestmark = pytest.mark.skipif(
    not DSN or not _can_connect(DSN),
    reason="DATABASE_URL indisponível / Postgres inacessível",
)


@pytest.fixture
def db_conn():
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    try:
        yield conn
        conn.rollback()
    finally:
        conn.close()


@pytest.fixture
def usuario_id(db_conn):
    """Usuário efêmero; rollback no fim do teste limpa tudo."""
    phone = f"55{uuid.uuid4().int % 10**11:011d}"
    with db_conn.cursor() as cur:
        # schema mínimo compatível com staging/local
        cur.execute(
            """
            INSERT INTO public.usuarios (numero_telefone, nome, perfil_tipo)
            VALUES (%s, %s, 'mei')
            RETURNING id
            """,
            (phone, f"IT OnConflict {phone[-4:]}"),
        )
        uid = cur.fetchone()[0]
    db_conn.commit()
    yield uid
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM public.agendamentos WHERE usuario_id = %s", (uid,))
        cur.execute("DELETE FROM public.usuarios WHERE id = %s", (uid,))
    db_conn.commit()


def test_constraint_existe(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conname = 'unique_agendamento_por_usuario'
            """
        )
        assert cur.fetchone() is not None


def test_create_on_conflict_reusa_registro(db_conn, usuario_id):
    payload = {
        "nome_compromisso": f"IT Plantao {uuid.uuid4().hex[:8]}",
        "data_compromisso": (date.today() + timedelta(days=7)).isoformat(),
        "hora_compromisso": "15:30",
        "lembrete_minutos_antes": 15,
    }

    first = q.create(db_conn, usuario_id, payload)
    db_conn.commit()
    assert first["created"] is True
    assert first["id"]

    second = q.create(db_conn, usuario_id, payload)
    db_conn.commit()
    assert second["created"] is False
    assert second["id"] == first["id"]

    with db_conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT COUNT(*)::int AS n
            FROM public.agendamentos
            WHERE usuario_id = %s
              AND nome_compromisso = %s
              AND data_compromisso = %s::date
              AND hora_compromisso = %s::time
            """,
            (
                usuario_id,
                payload["nome_compromisso"],
                payload["data_compromisso"],
                payload["hora_compromisso"],
            ),
        )
        assert cur.fetchone()["n"] == 1


def test_insert_cru_ainda_respeita_unique(db_conn, usuario_id):
    """Garante que a constraint no Postgres é a fonte da verdade (sem passar por q.create)."""
    nome = f"IT Raw {uuid.uuid4().hex[:8]}"
    data = (date.today() + timedelta(days=8)).isoformat()
    hora = "16:00"
    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO public.agendamentos (
                usuario_id, nome_compromisso, data_compromisso, hora_compromisso,
                status, lembrete_minutos_antes, data_criacao, data_modificacao
            ) VALUES (%s, %s, %s::date, %s::time, 'confirmado', 15, NOW(), NOW())
            RETURNING id
            """,
            (usuario_id, nome, data, hora),
        )
        first_id = cur.fetchone()[0]
        db_conn.commit()

        with pytest.raises(psycopg2.errors.UniqueViolation):
            cur.execute(
                """
                INSERT INTO public.agendamentos (
                    usuario_id, nome_compromisso, data_compromisso, hora_compromisso,
                    status, lembrete_minutos_antes, data_criacao, data_modificacao
                ) VALUES (%s, %s, %s::date, %s::time, 'confirmado', 15, NOW(), NOW())
                """,
                (usuario_id, nome, data, hora),
            )
        db_conn.rollback()

        # ON CONFLICT DO NOTHING não levanta e não cria 2ª linha
        cur.execute(
            """
            INSERT INTO public.agendamentos (
                usuario_id, nome_compromisso, data_compromisso, hora_compromisso,
                status, lembrete_minutos_antes, data_criacao, data_modificacao
            ) VALUES (%s, %s, %s::date, %s::time, 'confirmado', 15, NOW(), NOW())
            ON CONFLICT ON CONSTRAINT unique_agendamento_por_usuario DO NOTHING
            RETURNING id
            """,
            (usuario_id, nome, data, hora),
        )
        assert cur.fetchone() is None
        db_conn.commit()

        cur.execute(
            """
            SELECT COUNT(*)::int FROM public.agendamentos
            WHERE usuario_id = %s AND nome_compromisso = %s
              AND data_compromisso = %s::date AND hora_compromisso = %s::time
            """,
            (usuario_id, nome, data, hora),
        )
        assert cur.fetchone()[0] == 1
        assert first_id is not None
