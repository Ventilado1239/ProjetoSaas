import io
import logging
from datetime import date
from typing import Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

logger = logging.getLogger(__name__)


def hex_to_color(hex_str: str) -> colors.Color:
    """Convert a hex color string like '#2563eb' to a ReportLab Color."""
    hex_str = hex_str.lstrip("#")
    if len(hex_str) != 6:
        return colors.HexColor("#2563eb")
    return colors.HexColor(f"#{hex_str}")


def gerar_pdf_fechamento_diario(
    tenant_nome: str,
    cor_primaria: str,
    data_relatorio: date,
    dados: Dict[str, Any]
) -> bytes:
    """
    Generates a daily closing PDF report.

    Args:
        tenant_nome: Name of the tenant/business.
        cor_primaria: Primary hex color for theming.
        data_relatorio: The date this report covers.
        dados: Dictionary with keys:
            - total_atendimentos (int)
            - realizados (int)
            - faltas (int)
            - cancelados (int)
            - em_producao (int)
            - receita_total (float)
            - receita_recebida (float)
            - receita_pendente (float)
            - mensagens_noturnas (int)
            - atendimentos (list of dicts with 'horario', 'cliente', 'servico', 'status')

    Returns:
        PDF content as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    primary = hex_to_color(cor_primaria)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        textColor=primary,
        fontSize=18,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "CustomSubtitle",
        parent=styles["Normal"],
        textColor=colors.gray,
        fontSize=10,
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        textColor=primary,
        fontSize=13,
        spaceBefore=16,
        spaceAfter=6,
    )
    body_style = styles["Normal"]

    elements = []

    # Header
    elements.append(Paragraph(f"📊 Relatório de Fechamento Diário", title_style))
    elements.append(Paragraph(
        f"{tenant_nome} — {data_relatorio.strftime('%d/%m/%Y')}",
        subtitle_style
    ))
    elements.append(HRFlowable(width="100%", color=primary, thickness=1.5))
    elements.append(Spacer(1, 8 * mm))

    # Summary metrics
    elements.append(Paragraph("Resumo do Dia", section_style))

    summary_data = [
        ["Métrica", "Valor"],
        ["Total de Atendimentos", str(dados.get("total_atendimentos", 0))],
        ["Realizados / Entregues", str(dados.get("realizados", 0))],
        ["Faltas", str(dados.get("faltas", 0))],
        ["Cancelados", str(dados.get("cancelados", 0))],
        ["Em Produção", str(dados.get("em_producao", 0))],
        ["Mensagens Noturnas", str(dados.get("mensagens_noturnas", 0))],
    ]

    summary_table = Table(summary_data, colWidths=[120 * mm, 40 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6 * mm))

    # Financial section
    elements.append(Paragraph("Financeiro", section_style))
    receita_total = dados.get("receita_total", 0.0)
    receita_recebida = dados.get("receita_recebida", 0.0)
    receita_pendente = dados.get("receita_pendente", 0.0)

    fin_data = [
        ["", "Valor (R$)"],
        ["Receita Total", f"R$ {receita_total:,.2f}"],
        ["Receita Recebida", f"R$ {receita_recebida:,.2f}"],
        ["Receita Pendente", f"R$ {receita_pendente:,.2f}"],
    ]
    fin_table = Table(fin_data, colWidths=[120 * mm, 40 * mm])
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(fin_table)
    elements.append(Spacer(1, 6 * mm))

    # Appointment details table
    atendimentos: List[Dict] = dados.get("atendimentos", [])
    if atendimentos:
        elements.append(Paragraph("Detalhes dos Atendimentos", section_style))
        appt_data = [["Horário", "Cliente", "Serviço", "Status"]]
        for a in atendimentos:
            appt_data.append([
                a.get("horario", "-"),
                a.get("cliente", "-"),
                a.get("servico", "-"),
                a.get("status", "-"),
            ])

        appt_table = Table(appt_data, colWidths=[30 * mm, 50 * mm, 50 * mm, 30 * mm])
        appt_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(appt_table)

    # Footer
    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", color=colors.lightgrey, thickness=0.5))
    elements.append(Paragraph(
        f"Gerado automaticamente pelo SaaS de Gestão via WhatsApp — {tenant_nome}",
        ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.gray, alignment=1)
    ))

    doc.build(elements)
    return buffer.getvalue()


def gerar_pdf_roi_mensal(
    tenant_nome: str,
    cor_primaria: str,
    mes_ano: str,
    dados: Dict[str, Any]
) -> bytes:
    """
    Generates a monthly ROI executive report PDF.

    Args:
        tenant_nome: Name of the business.
        cor_primaria: Hex primary color.
        mes_ano: "MM/YYYY" label.
        dados: Dictionary with keys:
            - total_atendimentos (int)
            - taxa_comparecimento (float, 0-100)
            - receita_total (float)
            - receita_perdida_faltas (float)
            - reativados_crm (int)
            - consultas_lista_espera (int)
            - impacto_total (float)
            - mensalidade (float)
            - roi (float, ratio)

    Returns:
        PDF content as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    primary = hex_to_color(cor_primaria)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ROITitle", parent=styles["Title"], textColor=primary, fontSize=20, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "ROISubtitle", parent=styles["Normal"], textColor=colors.gray, fontSize=10, spaceAfter=12
    )
    section_style = ParagraphStyle(
        "ROISection", parent=styles["Heading2"], textColor=primary, fontSize=13, spaceBefore=14, spaceAfter=6
    )
    roi_highlight = ParagraphStyle(
        "ROIHighlight", parent=styles["Title"], textColor=colors.HexColor("#10b981"), fontSize=24, alignment=1
    )
    body_style = styles["Normal"]

    elements = []

    elements.append(Paragraph("📈 Relatório Mensal de ROI", title_style))
    elements.append(Paragraph(f"{tenant_nome} — {mes_ano}", subtitle_style))
    elements.append(HRFlowable(width="100%", color=primary, thickness=1.5))
    elements.append(Spacer(1, 8 * mm))

    # ROI Highlight
    roi_val = dados.get("roi", 0.0)
    impacto = dados.get("impacto_total", 0.0)
    mensalidade = dados.get("mensalidade", 0.0)

    elements.append(Paragraph("Retorno sobre Investimento (ROI)", section_style))
    elements.append(Paragraph(f"ROI: {roi_val:.1f}x", roi_highlight))
    elements.append(Paragraph(
        f"Impacto Total: R$ {impacto:,.2f} / Mensalidade: R$ {mensalidade:,.2f}",
        ParagraphStyle("ROISub", parent=body_style, alignment=1, textColor=colors.gray, fontSize=10)
    ))
    elements.append(Spacer(1, 8 * mm))

    # Performance metrics
    elements.append(Paragraph("Métricas de Performance", section_style))
    perf_data = [
        ["Indicador", "Valor"],
        ["Total de Atendimentos", str(dados.get("total_atendimentos", 0))],
        ["Taxa de Comparecimento", f"{dados.get('taxa_comparecimento', 0):.1f}%"],
        ["Receita Total", f"R$ {dados.get('receita_total', 0):,.2f}"],
        ["Receita Perdida (Faltas)", f"R$ {dados.get('receita_perdida_faltas', 0):,.2f}"],
        ["Pacientes Reativados pelo CRM", str(dados.get("reativados_crm", 0))],
        ["Consultas via Lista de Espera", str(dados.get("consultas_lista_espera", 0))],
    ]

    perf_table = Table(perf_data, colWidths=[120 * mm, 40 * mm])
    perf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(perf_table)

    # Footer
    elements.append(Spacer(1, 12 * mm))
    elements.append(HRFlowable(width="100%", color=colors.lightgrey, thickness=0.5))
    elements.append(Paragraph(
        f"Gerado automaticamente pelo SaaS de Gestão via WhatsApp — {tenant_nome}",
        ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.gray, alignment=1)
    ))

    doc.build(elements)
    return buffer.getvalue()
