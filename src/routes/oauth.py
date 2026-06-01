from flask import Blueprint, request
from functools import wraps
from datetime import datetime
import traceback

from src.db import get_db_conn
from src.utils.api_response import ok, fail

oauth_bp = Blueprint("oauth", __name__)


def require_user_id(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return fail("header_obrigatorio", "X-User-ID header required", 400)
        return f(*args, user_id=user_id, **kwargs)
    return decorated


@oauth_bp.get('/oauth/health')
def oauth_health():
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT current_database() AS db, NOW() AS ts')
                row = cur.fetchone()
        return ok(200, {'database': row['db'], 'server_time': row['ts'].isoformat()})
    except Exception as e:
        return fail("db_error", str(e), 500)


@oauth_bp.post('/oauth/refresh')
@require_user_id
def refresh_token(user_id):
    """Renova o access_token usando refresh_token armazenado."""
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT refresh_token, access_token, expires_at
                    FROM public.usuarios_google_oauth
                    WHERE usuario_id = %s
                      AND deleted_at IS NULL
                      AND is_active = true
                      AND revoked_at IS NULL
                """, (user_id,))
                result = cur.fetchone()

                if not result or not result['refresh_token']:
                    return fail("token_not_found", "Refresh token not found or inactive", 404)

                # TODO: chamada real ao Google OAuth2 token endpoint
                new_access_token = f"new_token_{datetime.now().timestamp()}"
                new_expires_at = datetime.now()

                cur.execute("""
                    UPDATE public.usuarios_google_oauth
                    SET access_token = %s,
                        expires_at = %s,
                        last_refreshed_at = NOW(),
                        updated_by = 'oauth_blueprint',
                        updated_reason = 'auto_refresh'
                    WHERE usuario_id = %s
                """, (new_access_token, new_expires_at, user_id))

        return ok(200, {
            'access_token': new_access_token,
            'expires_at': new_expires_at.isoformat(),
            'token_type': 'Bearer',
        })

    except Exception as e:
        print(f"[oauth] refresh error: {traceback.format_exc()}")
        return fail("refresh_error", str(e), 500)


@oauth_bp.post('/oauth/revoke')
@require_user_id
def revoke_token(user_id):
    """Revoga token (soft delete)."""
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE public.usuarios_google_oauth
                    SET is_active = false,
                        revoked_at = NOW(),
                        deleted_at = NOW(),
                        updated_by = 'oauth_blueprint',
                        updated_reason = 'user_revoked'
                    WHERE usuario_id = %s
                      AND deleted_at IS NULL
                """, (user_id,))
                if cur.rowcount == 0:
                    return fail("not_found", "User not found or already revoked", 404)

        return ok(200, {'revoked_at': datetime.now().isoformat()})

    except Exception as e:
        print(f"[oauth] revoke error: {traceback.format_exc()}")
        return fail("revoke_error", str(e), 500)


@oauth_bp.get('/oauth/status')
@require_user_id
def check_status(user_id):
    """Verifica status do token do usuário."""
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT is_active, expires_at, last_refreshed_at,
                           revoked_at, deleted_at, error_count,
                           last_error_message, authorized_at
                    FROM public.usuarios_google_oauth
                    WHERE usuario_id = %s
                    ORDER BY authorized_at DESC
                    LIMIT 1
                """, (user_id,))
                result = cur.fetchone()

        if not result:
            return fail("not_found", "User not found", 404)

        return ok(200, {
            'is_active':      result['is_active'],
            'is_revoked':     result['revoked_at'] is not None,
            'is_deleted':     result['deleted_at'] is not None,
            'expires_at':     result['expires_at'].isoformat()        if result['expires_at']        else None,
            'last_refreshed': result['last_refreshed_at'].isoformat() if result['last_refreshed_at'] else None,
            'error_count':    result['error_count'],
            'authorized_at':  result['authorized_at'].isoformat()     if result['authorized_at']     else None,
        })

    except Exception as e:
        return fail("status_error", str(e), 500)
