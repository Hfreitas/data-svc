"""
Queries do inbox multiusuário (schema `inbox`) — funções puras conn + params -> rows.
Doc: meire/docs/architecture/21-inbox-multiusuario-whatsapp.md
"""
from psycopg2.extras import RealDictCursor


# ============ ACCOUNTS ============

def create_account(conn, data: dict) -> dict:
    params = {
        "usuario_id": data.get("usuario_id"),
        "phone_number": data.get("phone_number"),
        "company_name": data.get("company_name"),
    }
    sql = """
        INSERT INTO inbox.whatsapp_account (usuario_id, phone_number, company_name)
        VALUES (%(usuario_id)s, %(phone_number)s, %(company_name)s)
        ON CONFLICT (phone_number) DO UPDATE
            SET company_name = COALESCE(EXCLUDED.company_name, inbox.whatsapp_account.company_name),
                usuario_id   = COALESCE(EXCLUDED.usuario_id, inbox.whatsapp_account.usuario_id)
        RETURNING id, usuario_id, phone_number, company_name, status, created_at;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return dict(cur.fetchone())


def get_account_by_phone(conn, phone_number: str) -> dict | None:
    sql = """
        SELECT id, usuario_id, phone_number, company_name, status, created_at
        FROM inbox.whatsapp_account
        WHERE phone_number = %(phone_number)s;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"phone_number": phone_number})
        row = cur.fetchone()
        return dict(row) if row else None


# ============ CONTACTS ============

def upsert_contact(conn, account_id: int, data: dict) -> dict:
    params = {
        "account_id": account_id,
        "phone_number": data.get("phone_number"),
        "name": data.get("name"),
    }
    sql = """
        INSERT INTO inbox.contact (whatsapp_account_id, phone_number, name)
        VALUES (%(account_id)s, %(phone_number)s, %(name)s)
        ON CONFLICT (whatsapp_account_id, phone_number) DO UPDATE
            SET name = COALESCE(EXCLUDED.name, inbox.contact.name)
        RETURNING id, whatsapp_account_id, phone_number, name, created_at;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return dict(cur.fetchone())


# ============ CONVERSATIONS ============

def open_or_get_conversation(conn, account_id: int, contact_id: int) -> dict:
    """Retorna a conversa aberta do contato ou cria uma nova (idempotente p/ inbound)."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, whatsapp_account_id, contact_id, status, opened_at, closed_at
            FROM inbox.conversation
            WHERE whatsapp_account_id = %(account_id)s
                AND contact_id = %(contact_id)s
                AND status = 'open'
            ORDER BY opened_at DESC
            LIMIT 1;
            """,
            {"account_id": account_id, "contact_id": contact_id},
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        cur.execute(
            """
            INSERT INTO inbox.conversation (whatsapp_account_id, contact_id)
            VALUES (%(account_id)s, %(contact_id)s)
            RETURNING id, whatsapp_account_id, contact_id, status, opened_at, closed_at;
            """,
            {"account_id": account_id, "contact_id": contact_id},
        )
        return dict(cur.fetchone())


def list_conversations(conn, account_id: int, status: str | None = None) -> list[dict]:
    sql = """
        SELECT
            c.id,
            c.contact_id,
            ct.name AS contact_name,
            ct.phone_number AS contact_phone,
            c.status,
            c.opened_at,
            c.closed_at,
            (SELECT content FROM inbox.message m
                WHERE m.conversation_id = c.id
                ORDER BY m.created_at DESC LIMIT 1) AS last_message
        FROM inbox.conversation c
        JOIN inbox.contact ct ON ct.id = c.contact_id
        WHERE c.whatsapp_account_id = %(account_id)s
            AND (%(status)s IS NULL OR c.status = %(status)s)
        ORDER BY c.opened_at DESC;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"account_id": account_id, "status": status})
        return [dict(r) for r in cur.fetchall()]


# ============ MESSAGES ============

def create_message(conn, data: dict) -> dict:
    """Insere mensagem e, se enviada por company_user, grava message_user (auditoria)."""
    params = {
        "conversation_id": data.get("conversation_id"),
        "sender_type": data.get("sender_type"),
        "sender_id": data.get("sender_id"),
        "message_type": data.get("message_type") or "text",
        "content": data.get("content"),
    }
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO inbox.message
                (conversation_id, sender_type, sender_id, message_type, content)
            VALUES
                (%(conversation_id)s, %(sender_type)s, %(sender_id)s, %(message_type)s, %(content)s)
            RETURNING id, conversation_id, sender_type, sender_id, message_type, content, created_at;
            """,
            params,
        )
        message = dict(cur.fetchone())

        # auditoria: só quando remetente é um usuário da empresa
        if message["sender_type"] == "user" and message["sender_id"] is not None:
            cur.execute(
                """
                INSERT INTO inbox.message_user (message_id, user_id)
                VALUES (%(message_id)s, %(user_id)s)
                ON CONFLICT (message_id, user_id) DO NOTHING;
                """,
                {"message_id": message["id"], "user_id": message["sender_id"]},
            )

        return message


def list_messages(conn, conversation_id: int, limit: int = 50, before_id: int | None = None) -> list[dict]:
    sql = """
        SELECT id, conversation_id, sender_type, sender_id, message_type, content, created_at
        FROM inbox.message
        WHERE conversation_id = %(conversation_id)s
            AND (%(before_id)s IS NULL OR id < %(before_id)s)
        ORDER BY id DESC
        LIMIT %(limit)s;
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, {"conversation_id": conversation_id, "before_id": before_id, "limit": limit})
        rows = [dict(r) for r in cur.fetchall()]
        rows.reverse()  # cronológico asc para o cliente
        return rows
