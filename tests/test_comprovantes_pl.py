"""Tests for PL support in comprovantes routes and queries."""
import pytest
from decimal import Decimal
from psycopg2.extras import RealDictCursor
from unittest.mock import MagicMock

import src.queries.comprovantes as q
from src.utils.validators import validate_comprovante_payload


class TestComprovantePLValidator:
    """Tests for PL field validation and passthrough."""

    def test_validate_comprovante_payload_passes_pl_fields(self):
        """Valida que os campos PL são passados sem erro."""
        body = {
            "operacao": "venda",
            "item": "Consultoria",
            "item_hash": "hash123",
            "quantidade": 1,
            "valor_unitario": 100.00,
            "valor_total": 100.00,
            "data_venda": "2025-01-10",
            "canal_venda": "presencial",
            "pagador_nome": "João Silva",
            "pagador_cpf": "12345678900",
            "atendido_nome": "Maria Santos",
            "atendido_cpf": "98765432100",
            "natureza_pagamento": "Prestação de Serviço",
        }

        result = validate_comprovante_payload(body)

        assert result["operacao"] == "venda"
        assert result["pagador_nome"] == "João Silva"
        assert result["pagador_cpf"] == "12345678900"
        assert result["atendido_nome"] == "Maria Santos"
        assert result["atendido_cpf"] == "98765432100"
        assert result["natureza_pagamento"] == "Prestação de Serviço"

    def test_validate_comprovante_payload_pl_fields_optional(self):
        """Valida que campos PL são opcionais (MEI não os usa)."""
        body = {
            "operacao": "venda",
            "item": "Venda",
            "item_hash": "hash456",
            "quantidade": 1,
            "valor_unitario": 50.00,
            "valor_total": 50.00,
            "data_venda": "2025-01-10",
        }

        result = validate_comprovante_payload(body)

        assert result["pagador_nome"] is None
        assert result["pagador_cpf"] is None
        assert result["atendido_nome"] is None
        assert result["atendido_cpf"] is None
        assert result["natureza_pagamento"] is None

    def test_validate_comprovante_payload_pl_fields_normalized(self):
        """Valida que campos PL com espaços são normalizados."""
        body = {
            "operacao": "gasto",
            "item": "Gastos",
            "item_hash": "hash789",
            "quantidade": 2,
            "valor_unitario": 25.00,
            "valor_total": 50.00,
            "data_compra": "2025-01-10",
            "pagador_nome": "  João Silva  ",
            "pagador_cpf": "",  # empty string -> None
            "atendido_nome": None,
            "atendido_cpf": "12345678900",
        }

        result = validate_comprovante_payload(body)

        assert result["pagador_nome"] == "João Silva"
        assert result["pagador_cpf"] is None
        assert result["atendido_nome"] is None
        assert result["atendido_cpf"] == "12345678900"


class TestComprovantePLQueries:
    """Tests for PL-related query functions."""

    def test_upsert_with_pl_fields(self, mocker):
        """Testa que upsert insere/atualiza campos PL corretamente."""
        mock_cursor = MagicMock()
        mock_row = {
            "id": 1,
            "operacao": "venda",
            "item": "Consultoria",
            "valor_total": Decimal("100.00"),
            "data_compra": None,
            "data_venda": "2025-01-10",
            "canal_venda": "presencial",
            "pagador_nome": "João Silva",
            "pagador_cpf": "12345678900",
            "atendido_nome": "Maria Santos",
            "atendido_cpf": "98765432100",
            "natureza_pagamento": "Prestação de Serviço",
        }
        mock_cursor.fetchone.return_value = mock_row

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        data = {
            "item": "Consultoria",
            "quantidade": 1,
            "valor_unitario": 100.00,
            "valor_total": 100.00,
            "operacao": "venda",
            "item_hash": "hash123",
            "data_venda": "2025-01-10",
            "canal_venda": "presencial",
            "pagador_nome": "João Silva",
            "pagador_cpf": "12345678900",
            "atendido_nome": "Maria Santos",
            "atendido_cpf": "98765432100",
            "natureza_pagamento": "Prestação de Serviço",
        }

        result = q.upsert(mock_conn, 123, data)

        assert result["pagador_nome"] == "João Silva"
        assert result["pagador_cpf"] == "12345678900"
        assert result["atendido_nome"] == "Maria Santos"
        assert result["atendido_cpf"] == "98765432100"
        assert result["natureza_pagamento"] == "Prestação de Serviço"

        # Verifica que o SQL contém os campos PL
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "pagador_nome" in sql
        assert "pagador_cpf" in sql
        assert "atendido_nome" in sql
        assert "atendido_cpf" in sql
        assert "natureza_pagamento" in sql

    def test_update_ultimo_with_values(self, mocker):
        """Testa que update_ultimo atualiza o último comprovante."""
        mock_cursor = MagicMock()
        mock_row = {
            "id": 99,
            "operacao": "venda",
            "item": "Consultoria Atualizada",
            "valor_total": Decimal("200.00"),
        }
        mock_cursor.fetchone.return_value = mock_row

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        result = q.update_ultimo(mock_conn, 123, valor_total=200.00, item="Consultoria Atualizada")

        assert result["id"] == 99
        assert result["valor_total"] == Decimal("200.00")
        assert result["item"] == "Consultoria Atualizada"

    def test_update_ultimo_returns_none_when_not_found(self, mocker):
        """Testa que update_ultimo retorna None quando nenhum comprovante existe."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        result = q.update_ultimo(mock_conn, 999, valor_total=100.00)

        assert result is None

    def test_delete_ultimo_success(self, mocker):
        """Testa que delete_ultimo deleta o último comprovante."""
        mock_cursor = MagicMock()
        mock_row = {"id": 99}
        mock_cursor.fetchone.return_value = mock_row

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        result = q.delete_ultimo(mock_conn, 123)

        assert result["id"] == 99

    def test_delete_ultimo_returns_none_when_not_found(self, mocker):
        """Testa que delete_ultimo retorna None quando nenhum comprovante existe."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        result = q.delete_ultimo(mock_conn, 999)

        assert result is None

    def test_get_livro_caixa_aggregation(self, mocker):
        """Testa que get_livro_caixa retorna agregação correta."""
        mock_cursor = MagicMock()
        mock_row = {
            "total_rendimentos": Decimal("500.00"),
            "total_pagamentos": Decimal("200.00"),
            "saldo": Decimal("300.00"),
            "total_sessoes": 5,
            "ticket_medio": Decimal("100.00"),
        }
        mock_cursor.fetchone.return_value = mock_row

        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        result = q.get_livro_caixa(mock_conn, 123, "2025-01")

        assert result["total_rendimentos"] == Decimal("500.00")
        assert result["total_pagamentos"] == Decimal("200.00")
        assert result["saldo"] == Decimal("300.00")
        assert result["total_sessoes"] == 5
        assert result["ticket_medio"] == Decimal("100.00")

        # Verifica que o SQL filtra por mês
        call_args = mock_cursor.execute.call_args
        assert call_args[0][1]["mes"] == "2025-01"


class TestComprovantePLRoutes:
    """Tests for PL-related route endpoints."""

    def test_patch_comprovante_ultimo_success(self, client, mocker):
        """Testa PATCH /usuarios/<id>/comprovantes/ultimo com sucesso."""
        mock_patch, mock_conn = mocker.patch(
            "src.routes.comprovantes.get_db_conn",
            return_value=MagicMock(__enter__=MagicMock(return_value=mocker.MagicMock()), __exit__=MagicMock())
        ), MagicMock()

        # Setup mock
        def get_db_conn_context():
            ctx = MagicMock()
            ctx.__enter__.return_value = mock_conn
            ctx.__exit__.return_value = False
            return ctx

        mock_patch.return_value = get_db_conn_context()

        # Mock the query function
        mock_comprovante = {
            "id": 99,
            "operacao": "venda",
            "item": "Consultoria Atualizada",
            "valor_total": 200.00,
        }
        mocker.patch(
            "src.routes.comprovantes.q.update_ultimo",
            return_value=mock_comprovante,
        )

        # Mock cache invalidate
        mocker.patch("src.routes.comprovantes.cache_invalidate_prefix")

        body = {"valor_total": 200.00, "item": "Consultoria Atualizada"}
        resp = client.patch(
            "/usuarios/123/comprovantes/ultimo",
            json=body,
            headers={"X-API-Key": "test-key"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == 99
        assert data["valor_total"] == 200.00

    def test_patch_comprovante_ultimo_not_found(self, client, mocker):
        """Testa PATCH /usuarios/<id>/comprovantes/ultimo retorna 404."""
        def get_db_conn_context():
            ctx = MagicMock()
            ctx.__enter__.return_value = MagicMock()
            ctx.__exit__.return_value = False
            return ctx

        mocker.patch(
            "src.routes.comprovantes.get_db_conn",
            return_value=get_db_conn_context(),
        )

        mocker.patch("src.routes.comprovantes.q.update_ultimo", return_value=None)

        body = {"valor_total": 200.00}
        resp = client.patch(
            "/usuarios/999/comprovantes/ultimo",
            json=body,
            headers={"X-API-Key": "test-key"},
        )

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "nao_encontrado"

    def test_delete_comprovante_ultimo_success(self, client, mocker):
        """Testa DELETE /usuarios/<id>/comprovantes/ultimo com sucesso."""
        def get_db_conn_context():
            ctx = MagicMock()
            ctx.__enter__.return_value = MagicMock()
            ctx.__exit__.return_value = False
            return ctx

        mocker.patch(
            "src.routes.comprovantes.get_db_conn",
            return_value=get_db_conn_context(),
        )

        mock_result = {"id": 99}
        mocker.patch("src.routes.comprovantes.q.delete_ultimo", return_value=mock_result)
        mocker.patch("src.routes.comprovantes.cache_invalidate_prefix")

        resp = client.delete(
            "/usuarios/123/comprovantes/ultimo",
            headers={"X-API-Key": "test-key"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == 99

    def test_delete_comprovante_ultimo_not_found(self, client, mocker):
        """Testa DELETE /usuarios/<id>/comprovantes/ultimo retorna 404."""
        def get_db_conn_context():
            ctx = MagicMock()
            ctx.__enter__.return_value = MagicMock()
            ctx.__exit__.return_value = False
            return ctx

        mocker.patch(
            "src.routes.comprovantes.get_db_conn",
            return_value=get_db_conn_context(),
        )

        mocker.patch("src.routes.comprovantes.q.delete_ultimo", return_value=None)

        resp = client.delete(
            "/usuarios/999/comprovantes/ultimo",
            headers={"X-API-Key": "test-key"},
        )

        assert resp.status_code == 404
        data = resp.get_json()
        assert data["error"] == "nao_encontrado"

    def test_get_livro_caixa_with_cache_miss(self, client, mocker):
        """Testa GET /usuarios/<id>/livro-caixa com cache miss."""
        def get_db_conn_context():
            ctx = MagicMock()
            ctx.__enter__.return_value = MagicMock()
            ctx.__exit__.return_value = False
            return ctx

        mocker.patch(
            "src.routes.comprovantes.get_db_conn",
            return_value=get_db_conn_context(),
        )

        mock_livro_caixa = {
            "total_rendimentos": Decimal("500.00"),
            "total_pagamentos": Decimal("200.00"),
            "saldo": Decimal("300.00"),
            "total_sessoes": 5,
            "ticket_medio": Decimal("100.00"),
        }
        mocker.patch("src.routes.comprovantes.q.get_livro_caixa", return_value=mock_livro_caixa)
        mocker.patch("src.routes.comprovantes.cache_get", return_value=None)
        mocker.patch("src.routes.comprovantes.cache_set")

        resp = client.get(
            "/usuarios/123/livro-caixa?mes=2025-01",
            headers={"X-API-Key": "test-key"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_rendimentos"] == 500.00
        assert data["saldo"] == 300.00

    def test_get_livro_caixa_invalid_mes(self, client, mocker):
        """Testa GET /usuarios/<id>/livro-caixa com mes inválido."""
        resp = client.get(
            "/usuarios/123/livro-caixa?mes=invalid",
            headers={"X-API-Key": "test-key"},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_create_comprovante_with_pl_fields(self, client, mocker):
        """Testa POST /usuarios/<id>/comprovantes com campos PL."""
        def get_db_conn_context():
            ctx = MagicMock()
            ctx.__enter__.return_value = MagicMock()
            ctx.__exit__.return_value = False
            return ctx

        mocker.patch(
            "src.routes.comprovantes.get_db_conn",
            return_value=get_db_conn_context(),
        )

        mock_comprovante = {
            "id": 1,
            "operacao": "venda",
            "item": "Consultoria",
            "valor_total": 100.00,
            "data_venda": "2025-01-10",
            "data_compra": None,
            "canal_venda": "presencial",
            "pagador_nome": "João Silva",
            "pagador_cpf": "12345678900",
            "atendido_nome": "Maria Santos",
            "atendido_cpf": "98765432100",
            "natureza_pagamento": "Prestação de Serviço",
        }
        mocker.patch("src.routes.comprovantes.q.upsert", return_value=mock_comprovante)
        mocker.patch("src.routes.comprovantes.cache_invalidate_prefix")

        body = {
            "operacao": "venda",
            "item": "Consultoria",
            "item_hash": "hash123",
            "quantidade": 1,
            "valor_unitario": 100.00,
            "valor_total": 100.00,
            "data_venda": "2025-01-10",
            "canal_venda": "presencial",
            "pagador_nome": "João Silva",
            "pagador_cpf": "12345678900",
            "atendido_nome": "Maria Santos",
            "atendido_cpf": "98765432100",
            "natureza_pagamento": "Prestação de Serviço",
        }

        resp = client.post(
            "/usuarios/123/comprovantes",
            json=body,
            headers={"X-API-Key": "test-key"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["pagador_nome"] == "João Silva"
        assert data["atendido_nome"] == "Maria Santos"
