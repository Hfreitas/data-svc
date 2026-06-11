"""
Geração de datas para agendamentos recorrentes.
"""
import calendar
from datetime import date, timedelta
from typing import Final

# Mapeamento de nomes em português para números de dia da semana (0=seg, 6=dom)
_WEEKDAY_MAP: Final[dict[str, int]] = {
    "seg": 0,
    "ter": 1,
    "qua": 2,
    "qui": 3,
    "sex": 4,
    "sab": 5,
    "dom": 6,
}


def generate_recurrence_dates(
    data_inicio: date,
    frequencia: str,
    dia_semana_ou_mes: str,
    quantidade_meses: int,
) -> list[date]:
    """
    Gera lista de datas para uma série recorrente.

    Args:
        data_inicio: Data do primeiro agendamento
        frequencia: 'semanal', 'quinzenal' ou 'mensal'
        dia_semana_ou_mes: Dia da semana (seg, ter, qua, qui, sex, sab, dom) ou dia do mês (1-31)
        quantidade_meses: Horizonte em meses (1-12)

    Returns:
        Lista de datas ordenadas

    Raises:
        ValueError: Se os parâmetros forem inválidos
    """
    if frequencia not in ("semanal", "quinzenal", "mensal"):
        raise ValueError(f"frequencia inválida: {frequencia}")

    if quantidade_meses < 1 or quantidade_meses > 12:
        raise ValueError(f"quantidade_meses deve estar entre 1 e 12, recebido: {quantidade_meses}")

    # Calcular data final (exatamente quantidade_meses meses depois)
    end_month = data_inicio.month + quantidade_meses
    end_year = data_inicio.year

    # Ajustar ano e mês se necessário
    if end_month > 12:
        end_month -= 12
        end_year += 1

    # Data final é o último dia do mês anterior ao que seria quantidade_meses depois
    try:
        # Tentar usar o mesmo dia da data_inicio
        data_final = date(end_year, end_month, data_inicio.day)
    except ValueError:
        # Se o dia não existir neste mês, usar o último dia do mês
        _, last_day = calendar.monthrange(end_year, end_month)
        data_final = date(end_year, end_month, last_day)

    datas = []

    if frequencia == "semanal":
        # Validar dia da semana
        if dia_semana_ou_mes not in _WEEKDAY_MAP:
            raise ValueError(f"dia_semana inválido: {dia_semana_ou_mes}. Esperado: seg, ter, qua, qui, sex, sab, dom")

        target_weekday = _WEEKDAY_MAP[dia_semana_ou_mes]
        current = data_inicio

        # Avançar para o primeiro dia da semana correto
        days_ahead = (target_weekday - current.weekday()) % 7
        if days_ahead > 0:
            current = current + timedelta(days=days_ahead)

        while current <= data_final:
            datas.append(current)
            current = current + timedelta(weeks=1)

    elif frequencia == "quinzenal":
        # Validar dia da semana
        if dia_semana_ou_mes not in _WEEKDAY_MAP:
            raise ValueError(f"dia_semana inválido: {dia_semana_ou_mes}. Esperado: seg, ter, qua, qui, sex, sab, dom")

        target_weekday = _WEEKDAY_MAP[dia_semana_ou_mes]
        current = data_inicio

        # Avançar para o primeiro dia da semana correto
        days_ahead = (target_weekday - current.weekday()) % 7
        if days_ahead > 0:
            current = current + timedelta(days=days_ahead)

        while current <= data_final:
            datas.append(current)
            current = current + timedelta(weeks=2)

    elif frequencia == "mensal":
        # Validar dia do mês
        try:
            dia_mes = int(dia_semana_ou_mes)
        except ValueError:
            raise ValueError(f"dia_semana_ou_mes deve ser um número para frequência 'mensal': {dia_semana_ou_mes}")

        if dia_mes < 1 or dia_mes > 31:
            raise ValueError(f"dia_mes deve estar entre 1 e 31, recebido: {dia_mes}")

        year, month = data_inicio.year, data_inicio.month

        while True:
            # Tentar usar o dia especificado; se não existir, usar o último dia do mês
            try:
                current = date(year, month, dia_mes)
            except ValueError:
                _, last_day = calendar.monthrange(year, month)
                current = date(year, month, last_day)

            if current > data_final:
                break

            if current >= data_inicio:
                datas.append(current)

            # Próximo mês
            month += 1
            if month > 12:
                month = 1
                year += 1

    return sorted(datas)
