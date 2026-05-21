"""
Testes para a geração de datas de recorrência.
"""
from datetime import date, timedelta
import pytest

from src.utils.recurrence_generator import generate_recurrence_dates


class TestGenerateRecurrenceDates:
    def test_semanal_gera_datas_corretas(self):
        """Testa geração de datas semanais."""
        data_inicio = date(2026, 5, 11)  # Segunda-feira
        datas = generate_recurrence_dates(data_inicio, "semanal", "seg", 1)
        
        assert len(datas) >= 4  # Mínimo de 4 segundas em um mês
        assert all(d.weekday() == 0 for d in datas)  # Todos são segundas
        assert datas[0] >= data_inicio

    def test_semanal_com_diferentes_dias(self):
        """Testa geração de datas em diferentes dias da semana."""
        data_inicio = date(2026, 5, 11)
        
        for dia, weekday_num in [("seg", 0), ("ter", 1), ("qua", 2), ("qui", 3), ("sex", 4), ("sab", 5), ("dom", 6)]:
            datas = generate_recurrence_dates(data_inicio, "semanal", dia, 1)
            assert all(d.weekday() == weekday_num for d in datas), f"Falha para dia {dia}"

    def test_quinzenal_gera_datas_a_cada_2_semanas(self):
        """Testa geração de datas quinzenais."""
        data_inicio = date(2026, 5, 11)  # Segunda-feira
        datas = generate_recurrence_dates(data_inicio, "quinzenal", "seg", 2)
        
        assert len(datas) >= 2  # Mínimo de 2 datas em 2 meses
        # Verificar intervalos de 14 dias
        for i in range(len(datas) - 1):
            diff = (datas[i+1] - datas[i]).days
            assert 13 <= diff <= 15, f"Intervalo inválido: {diff} dias"

    def test_mensal_gera_datas_no_mesmo_dia(self):
        """Testa geração de datas mensais."""
        data_inicio = date(2026, 5, 15)
        datas = generate_recurrence_dates(data_inicio, "mensal", "15", 3)
        
        assert len(datas) >= 3  # Mínimo de 3 meses
        assert all(d.day == 15 for d in datas)

    def test_mensal_com_dia_invalido_usa_ultimo_dia_mes(self):
        """Testa que meses com menos dias usam o último dia disponível."""
        data_inicio = date(2026, 1, 31)
        datas = generate_recurrence_dates(data_inicio, "mensal", "31", 3)
        
        assert len(datas) >= 2
        # 2026 não é bissexto, então fevereiro tem 28 dias
        assert datas[0].day == 31  # Janeiro
        assert datas[1].day == 28  # Fevereiro (último dia)

    def test_quantidade_meses_valida(self):
        """Testa validação de quantidade_meses."""
        data_inicio = date(2026, 5, 11)
        
        # Válido: 1 a 12
        for qty in [1, 6, 12]:
            datas = generate_recurrence_dates(data_inicio, "semanal", "seg", qty)
            assert len(datas) > 0
        
        # Inválido: < 1 ou > 12
        with pytest.raises(ValueError, match="quantidade_meses"):
            generate_recurrence_dates(data_inicio, "semanal", "seg", 0)
        
        with pytest.raises(ValueError, match="quantidade_meses"):
            generate_recurrence_dates(data_inicio, "semanal", "seg", 13)

    def test_frequencia_invalida(self):
        """Testa rejeição de frequência inválida."""
        data_inicio = date(2026, 5, 11)
        
        with pytest.raises(ValueError, match="frequencia inválida"):
            generate_recurrence_dates(data_inicio, "diaria", "seg", 1)

    def test_dia_semana_invalido_para_semanal(self):
        """Testa rejeição de dia da semana inválido."""
        data_inicio = date(2026, 5, 11)
        
        with pytest.raises(ValueError, match="dia_semana inválido"):
            generate_recurrence_dates(data_inicio, "semanal", "invalid", 1)

    def test_dia_mes_invalido_para_mensal(self):
        """Testa rejeição de dia do mês inválido."""
        data_inicio = date(2026, 5, 11)
        
        with pytest.raises(ValueError, match="dia_mes"):
            generate_recurrence_dates(data_inicio, "mensal", "32", 1)
        
        with pytest.raises(ValueError, match="dia_mes"):
            generate_recurrence_dates(data_inicio, "mensal", "0", 1)

    def test_datas_retornadas_em_ordem(self):
        """Testa que as datas são retornadas em ordem crescente."""
        data_inicio = date(2026, 5, 11)
        datas = generate_recurrence_dates(data_inicio, "semanal", "seg", 3)
        
        assert datas == sorted(datas)

    def test_semanal_quantidade_meses_12(self):
        """Testa geração com 12 meses."""
        data_inicio = date(2026, 1, 5)  # Segunda
        datas = generate_recurrence_dates(data_inicio, "semanal", "seg", 12)
        
        # Deve gerar aproximadamente 52-56 semanas (12 meses inteiros)
        assert len(datas) >= 52

    def test_mensal_quantidade_meses_12(self):
        """Testa geração mensal com 12 meses."""
        data_inicio = date(2026, 1, 15)
        datas = generate_recurrence_dates(data_inicio, "mensal", "15", 12)
        
        # Deve gerar 12-13 datas (um mês completo é gerado)
        assert len(datas) >= 12 and len(datas) <= 13

    def test_quinzenal_quantidade_meses_12(self):
        """Testa geração quinzenal com 12 meses."""
        data_inicio = date(2026, 1, 5)  # Segunda
        datas = generate_recurrence_dates(data_inicio, "quinzenal", "seg", 12)
        
        # Deve gerar aproximadamente 26 datas (a cada 2 semanas)
        assert len(datas) >= 24 and len(datas) <= 28
