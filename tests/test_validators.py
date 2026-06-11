"""
Testes unitários diretos para validators (sem Flask app / test client).
flask.abort() levanta werkzeug.exceptions.HTTPException diretamente — não precisa de app context.
"""
import pytest
from datetime import date, timedelta
from werkzeug.exceptions import HTTPException

from src.utils.recurrence_generator import generate_recurrence_dates
from src.utils.validators.agendamentos import validate_update_agendamento_payload
from src.utils.validators.contas import validate_conta_recorrente_payload


# ---------------------------------------------------------------------------
# recurrence_generator — mensal: datas antes de data_inicio
# ---------------------------------------------------------------------------

class TestRecurrenceGeneratorMensalEdgeCases:
    def test_dia_anterior_ao_inicio_nao_inclui_data_do_mes_inicial(self):
        """Bug fix: dia=1 com data_inicio=20/05 gerava 01/05 (antes do início)."""
        data_inicio = date(2026, 5, 20)
        datas = generate_recurrence_dates(data_inicio, "mensal", "1", 2)

        for d in datas:
            assert d >= data_inicio, f"Data {d} é anterior a data_inicio {data_inicio}"

    def test_dia_igual_ao_dia_inicio_inclui_primeiro_mes(self):
        """dia_mes == data_inicio.day → mês inicial incluído."""
        data_inicio = date(2026, 5, 15)
        datas = generate_recurrence_dates(data_inicio, "mensal", "15", 1)
        assert date(2026, 5, 15) in datas

    def test_dia_posterior_ao_dia_inicio_inclui_primeiro_mes(self):
        """dia_mes=28 com data_inicio.day=5 → dia ainda não passou: inclui maio."""
        data_inicio = date(2026, 5, 5)
        datas = generate_recurrence_dates(data_inicio, "mensal", "28", 1)
        assert date(2026, 5, 28) in datas

    def test_todas_datas_maiores_ou_iguais_a_inicio_varios_dias(self):
        """Invariante: nenhuma data antes de data_inicio, para qualquer dia do mês."""
        data_inicio = date(2026, 3, 15)
        for dia in ["1", "10", "14", "15", "20", "31"]:
            datas = generate_recurrence_dates(data_inicio, "mensal", dia, 3)
            for d in datas:
                assert d >= data_inicio, f"dia={dia}: {d} anterior a {data_inicio}"

    def test_mensal_virada_de_ano_datas_validas(self):
        """data_inicio em dezembro, quantidade_meses=2 → fevereiro do ano seguinte."""
        data_inicio = date(2026, 12, 10)
        datas = generate_recurrence_dates(data_inicio, "mensal", "10", 2)
        assert date(2026, 12, 10) in datas
        assert date(2027, 1, 10) in datas
        for d in datas:
            assert d >= data_inicio


# ---------------------------------------------------------------------------
# validate_update_agendamento_payload — nome_compromisso
# ---------------------------------------------------------------------------

class TestValidateUpdateAgendamentoNomeCompromisso:
    def test_nome_vazio_retorna_400(self):
        """Bug fix: antes, string vazia era silenciosamente dropada em vez de 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_update_agendamento_payload({"nome_compromisso": ""})
        assert exc_info.value.code == 400

    def test_nome_apenas_espacos_retorna_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_update_agendamento_payload({"nome_compromisso": "   "})
        assert exc_info.value.code == 400

    def test_nome_valido_incluido_no_resultado(self):
        result = validate_update_agendamento_payload({"nome_compromisso": "Reunião"})
        assert result["nome_compromisso"] == "Reunião"

    def test_nome_com_espacos_laterais_normalizado(self):
        """Bug fix: antes, '  Reunião  ' abortava 400 por `stripped != original`."""
        result = validate_update_agendamento_payload({"nome_compromisso": "  Reunião  "})
        assert result["nome_compromisso"] == "Reunião"

    def test_body_vazio_retorna_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_update_agendamento_payload({})
        assert exc_info.value.code == 400

    def test_status_invalido_retorna_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_update_agendamento_payload({"status": "inexistente"})
        assert exc_info.value.code == 400

    def test_status_valido_incluido_no_resultado(self):
        result = validate_update_agendamento_payload({"status": "cancelado"})
        assert result["status"] == "cancelado"

    def test_data_no_passado_retorna_400(self):
        data_passada = (date.today() - timedelta(days=1)).isoformat()
        with pytest.raises(HTTPException) as exc_info:
            validate_update_agendamento_payload({"data_compromisso": data_passada})
        assert exc_info.value.code == 400

    def test_hora_invalida_retorna_400(self):
        data_futura = (date.today() + timedelta(days=1)).isoformat()
        with pytest.raises(HTTPException) as exc_info:
            validate_update_agendamento_payload({
                "data_compromisso": data_futura,
                "hora_compromisso": "25:00",
            })
        assert exc_info.value.code == 400


# ---------------------------------------------------------------------------
# validate_conta_recorrente_payload — valor como número
# ---------------------------------------------------------------------------

class TestValidateContaRecorrenteValor:
    def _payload(self, **overrides):
        p = {"tipo": "internet", "descricao": "Plano fibra", "valor": "129.90", "dia_vencimento": 10}
        p.update(overrides)
        return p

    def test_valor_string_numerica_convertida_para_float(self):
        result = validate_conta_recorrente_payload(self._payload(valor="129.90"))
        assert result["valor"] == 129.9
        assert isinstance(result["valor"], float)

    def test_valor_inteiro_convertido_para_float(self):
        result = validate_conta_recorrente_payload(self._payload(valor=100))
        assert result["valor"] == 100.0

    def test_valor_nao_numerico_retorna_400(self):
        """Bug fix: antes, 'abc' chegava cru ao DB causando 500."""
        with pytest.raises(HTTPException) as exc_info:
            validate_conta_recorrente_payload(self._payload(valor="abc"))
        assert exc_info.value.code == 400

    def test_valor_none_retorna_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_conta_recorrente_payload(self._payload(valor=None))
        assert exc_info.value.code == 400

    def test_valor_string_vazia_retorna_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_conta_recorrente_payload(self._payload(valor=""))
        assert exc_info.value.code == 400

    def test_dia_vencimento_invalido_retorna_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_conta_recorrente_payload(self._payload(dia_vencimento=32))
        assert exc_info.value.code == 400

    def test_tipo_invalido_retorna_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_conta_recorrente_payload(self._payload(tipo="streaming"))
        assert exc_info.value.code == 400

    def test_payload_valido_retorna_resultado_normalizado(self):
        result = validate_conta_recorrente_payload(
            self._payload(valor="50.00", dia_vencimento=15, tipo="aluguel")
        )
        assert result["tipo"] == "aluguel"
        assert result["valor"] == 50.0
        assert result["dia_vencimento"] == 15
