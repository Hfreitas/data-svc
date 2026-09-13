"""Testes do PDF do Livro Caixa PL."""

from decimal import Decimal
from datetime import date

from src.pdf.livro_caixa import build_livro_caixa_pdf, pdf_to_base64_payload, mes_label, _money


def test_mes_label():
    assert mes_label("2026-09") == ("setembro", 2026)
    assert mes_label("2026-01") == ("janeiro", 2026)


def test_money_negative_and_thousands():
    assert _money(Decimal("-821.15")) == "R$-821,15"
    assert _money(Decimal("2990")) == "R$2.990,00"
    assert _money(Decimal("-1234567.89")) == "R$-1.234.567,89"
    assert _money(0) == "R$0,00"


def test_build_livro_caixa_pdf_bytes():
    payload = {
        "mes": "2026-09",
        "nome": "Joana",
        "descricao_negocio": "plantões em hospital e clínicas",
        "totais": {
            "total_rendimentos": Decimal("250.00"),
            "total_pagamentos": Decimal("150.00"),
            "saldo": Decimal("100.00"),
        },
        "pagamentos": [
            {
                "item": "Conta de telefone Mensal",
                "natureza_pagamento": "Telefone do escritório/Consultório",
                "valor": Decimal("150.00"),
                "data": date(2026, 9, 10),
            }
        ],
        "rendimentos": [
            {
                "item": "Plantão hospitalar",
                "valor": Decimal("250.00"),
                "data": date(2026, 9, 5),
                "pagador_nome": "Hospital X",
                "pagador_cpf": "12345678901",
                "atendido_nome": "Joana",
                "atendido_cpf": "12345678901",
            }
        ],
    }
    pdf_bytes = build_livro_caixa_pdf(payload)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500

    out = pdf_to_base64_payload(pdf_bytes, "2026-09", parcial=True)
    assert out["fileName"] == "Livro-Caixa-Parcial-setembro-2026.pdf"
    assert out["pdf_base64"]
    assert out["parcial"] is True


def test_build_livro_caixa_pdf_empty_month():
    payload = {
        "mes": "2026-09",
        "nome": "Marina",
        "descricao_negocio": "Consultório Marina",
        "totais": {
            "total_rendimentos": 0,
            "total_pagamentos": 0,
            "saldo": 0,
        },
        "pagamentos": [],
        "rendimentos": [],
    }
    pdf_bytes = build_livro_caixa_pdf(payload)
    assert pdf_bytes[:4] == b"%PDF"
