"""PDF do Livro Caixa PL — layout baseado em docs/assets/livro-caixa-mensal-design.pdf."""

from __future__ import annotations

import base64
import io
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_MES_NOMES = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

_FOOTER = (
    "O escritório Almeida & Oliveira é parceiro da MEIrelles - "
    "A Assistente do ZAP para Profissionais Liberais."
)

_DISCLAIMER = (
    "Este Livro Caixa não tem validade Legal, "
    "mas já está na ordem certa para você enviar para a Receita :)"
)


def _money(value: Any) -> str:
    try:
        n = Decimal(str(value if value is not None else 0))
    except Exception:
        n = Decimal("0")
    sign = "-" if n < 0 else ""
    s = f"{abs(n):.2f}".replace(".", ",")
    int_part, dec = s.split(",")
    groups = []
    while int_part:
        groups.append(int_part[-3:])
        int_part = int_part[:-3]
    int_fmt = ".".join(reversed(groups))
    return f"R${sign}{int_fmt},{dec}"


def _fmt_cpf(cpf: str | None) -> str:
    digits = "".join(c for c in str(cpf or "") if c.isdigit())
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return str(cpf or "").strip()


def _fmt_date(value: Any, style: str = "br") -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y" if style == "br" else "%d.%m.%y")
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        y, m, d = text[:10].split("-")
        return f"{d}/{m}/{y}" if style == "br" else f"{d}.{m}.{y[2:]}"
    return text


def mes_label(mes: str) -> tuple[str, int]:
    """Retorna (nome_do_mês, ano) a partir de YYYY-MM."""
    year, month = mes.split("-")
    idx = max(1, min(12, int(month))) - 1
    return _MES_NOMES[idx], int(year)


def build_livro_caixa_pdf(payload: dict) -> bytes:
    """Gera bytes do PDF a partir do payload detalhado."""
    mes = payload["mes"]
    mes_nome, ano = mes_label(mes)
    consultorio = (
        payload.get("descricao_negocio")
        or payload.get("nome")
        or "Consultório / Escritório"
    )
    totals = payload.get("totais") or {}
    pagamentos = list(payload.get("pagamentos") or [])
    rendimentos = list(payload.get("rendimentos") or [])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Livro Caixa de {mes_nome.capitalize()} de {ano}",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "LCTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    office_style = ParagraphStyle(
        "LCOffice",
        parent=styles["Normal"],
        fontName="Courier-Bold",
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=8,
        leading=20,
    )
    disclaimer_style = ParagraphStyle(
        "LCDisclaimer",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
        spaceAfter=14,
        leading=12,
    )
    section_style = ParagraphStyle(
        "LCSection",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        spaceBefore=10,
        spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "LCCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    )
    cell_right = ParagraphStyle(
        "LCCellRight",
        parent=cell_style,
        alignment=TA_RIGHT,
    )
    sub_style = ParagraphStyle(
        "LCSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        textColor=colors.HexColor("#444444"),
        leading=9,
    )
    footer_style = ParagraphStyle(
        "LCFooter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        leading=10,
    )
    summary_label = ParagraphStyle(
        "LCSumLabel",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=10,
        alignment=TA_LEFT,
    )
    summary_value = ParagraphStyle(
        "LCSumValue",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=10,
        alignment=TA_RIGHT,
    )

    story: list = []
    story.append(Paragraph(f"Livro Caixa de {mes_nome.capitalize()} de {ano}", title_style))
    story.append(Paragraph(str(consultorio), office_style))
    story.append(Paragraph(_DISCLAIMER, disclaimer_style))

    summary_rows = [
        [
            Paragraph("Saldo Total", summary_label),
            Paragraph(_money(totals.get("saldo")), summary_value),
        ],
        [
            Paragraph("Total Pagamentos", summary_label),
            Paragraph(_money(totals.get("total_pagamentos")), summary_value),
        ],
        [
            Paragraph("Total Rendimentos", summary_label),
            Paragraph(_money(totals.get("total_rendimentos")), summary_value),
        ],
    ]
    summary = Table(summary_rows, colWidths=[90 * mm, 70 * mm])
    summary.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(summary)
    story.append(Spacer(1, 8 * mm))

    # --- Pagamentos ---
    story.append(Paragraph("Pagamentos:", section_style))
    pag_header = [
        Paragraph("<b>No</b>", cell_style),
        Paragraph("<b>Natureza do Pagamento:</b>", cell_style),
        Paragraph("<b>Histórico:</b>", cell_style),
        Paragraph("<b>Data:</b>", cell_style),
        Paragraph("<b>Valor:</b>", cell_right),
    ]
    pag_data = [pag_header]
    for i, row in enumerate(pagamentos, start=1):
        natureza = row.get("natureza_pagamento") or row.get("item") or "—"
        historico = row.get("item") or "—"
        if row.get("natureza_pagamento") and row.get("item"):
            historico = row.get("item")
        pag_data.append(
            [
                Paragraph(f"{i:02d}", cell_style),
                Paragraph(str(natureza), cell_style),
                Paragraph(str(historico), cell_style),
                Paragraph(_fmt_date(row.get("data"), "br"), cell_style),
                Paragraph(_money(row.get("valor")), cell_right),
            ]
        )
    if not pagamentos:
        pag_data.append(
            [
                Paragraph("—", cell_style),
                Paragraph("Sem pagamentos neste mês", cell_style),
                Paragraph("", cell_style),
                Paragraph("", cell_style),
                Paragraph(_money(0), cell_right),
            ]
        )

    pag_table = Table(pag_data, colWidths=[12 * mm, 48 * mm, 55 * mm, 25 * mm, 28 * mm])
    pag_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(pag_table)
    story.append(Spacer(1, 3 * mm))
    tot_pag = Table(
        [[
            Paragraph("<b>Total de Pagamentos</b>", cell_style),
            Paragraph(f"<b>{_money(totals.get('total_pagamentos'))}</b>", cell_right),
        ]],
        colWidths=[130 * mm, 38 * mm],
    )
    tot_pag.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(tot_pag)

    # --- Rendimentos ---
    story.append(Paragraph("Rendimentos:", section_style))
    ren_header = [
        Paragraph("<b>No</b>", cell_style),
        Paragraph("<b>Descrição:</b>", cell_style),
        Paragraph("<b>Data</b>", cell_style),
        Paragraph("<b>Valor</b>", cell_right),
    ]
    ren_data = [ren_header]
    for i, row in enumerate(rendimentos, start=1):
        desc = str(row.get("item") or "—")
        pagador = row.get("pagador_nome") or ""
        pagador_cpf = _fmt_cpf(row.get("pagador_cpf"))
        benefic = row.get("atendido_nome") or row.get("pagador_nome") or ""
        benefic_cpf = _fmt_cpf(row.get("atendido_cpf") or row.get("pagador_cpf"))
        lines = [desc]
        if pagador or pagador_cpf:
            lines.append(f"Pagador: {pagador}{' - ' + pagador_cpf if pagador_cpf else ''}".strip())
        if benefic or benefic_cpf:
            lines.append(f"Benefic.: {benefic}{' - ' + benefic_cpf if benefic_cpf else ''}".strip())
        desc_para = "<br/>".join(
            f'<font size="8">{lines[0]}</font>'
            if idx == 0
            else f'<font size="7.5" color="#444444">{line}</font>'
            for idx, line in enumerate(lines)
        )
        ren_data.append(
            [
                Paragraph(str(i), cell_style),
                Paragraph(desc_para, cell_style),
                Paragraph(_fmt_date(row.get("data"), "dot"), cell_style),
                Paragraph(_money(row.get("valor")), cell_right),
            ]
        )
    if not rendimentos:
        ren_data.append(
            [
                Paragraph("—", cell_style),
                Paragraph("Sem rendimentos neste mês", cell_style),
                Paragraph("", cell_style),
                Paragraph(_money(0), cell_right),
            ]
        )

    ren_table = Table(ren_data, colWidths=[12 * mm, 103 * mm, 25 * mm, 28 * mm])
    ren_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(ren_table)
    story.append(Spacer(1, 3 * mm))
    tot_ren = Table(
        [[
            Paragraph("<b>Total de Rendimentos</b>", cell_style),
            Paragraph(f"<b>{_money(totals.get('total_rendimentos'))}</b>", cell_right),
        ]],
        colWidths=[130 * mm, 38 * mm],
    )
    tot_ren.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(tot_ren)

    def _on_page(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#AAAAAA"))
        canvas.setLineWidth(0.5)
        y = 12 * mm
        canvas.line(18 * mm, y + 8 * mm, A4[0] - 18 * mm, y + 8 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.drawCentredString(A4[0] / 2, y + 3 * mm, _FOOTER)
        canvas.drawCentredString(A4[0] / 2, y - 2 * mm, str(canvas.getPageNumber()))
        canvas.restoreState()

    # Spacer so content doesn't collide with footer on short pages
    story.append(Spacer(1, 10 * mm))
    # Keep unused imports referenced for future KeepTogether blocks
    _ = (KeepTogether, HRFlowable, sub_style)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


def pdf_to_base64_payload(pdf_bytes: bytes, mes: str, parcial: bool = True) -> dict:
    mes_nome, ano = mes_label(mes)
    kind = "Parcial" if parcial else "Completo"
    file_name = f"Livro-Caixa-{kind}-{mes_nome}-{ano}.pdf"
    return {
        "pdf_base64": base64.b64encode(pdf_bytes).decode("ascii"),
        "fileName": file_name,
        "mes": mes,
        "parcial": parcial,
        "content_type": "application/pdf",
    }
