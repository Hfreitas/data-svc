import psycopg2
import pytest

from src import db


def _make_conn(mocker, cursor_execute_side_effect=None):
    conn = mocker.MagicMock()
    cursor = mocker.MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False
    if cursor_execute_side_effect:
        cursor.execute.side_effect = cursor_execute_side_effect
    conn.cursor.return_value = cursor
    return conn


class TestGetHealthyConn:
    def test_retorna_conexao_saudavel_na_primeira_tentativa(self, mocker):
        conn = _make_conn(mocker)
        pool_mock = mocker.patch.object(db, "_pool")
        pool_mock.getconn.return_value = conn

        result = db._get_healthy_conn()

        assert result is conn
        pool_mock.putconn.assert_not_called()

    def test_descarta_conexao_morta_e_usa_a_proxima(self, mocker):
        conn_morta = _make_conn(
            mocker, cursor_execute_side_effect=psycopg2.OperationalError("server closed the connection unexpectedly")
        )
        conn_saudavel = _make_conn(mocker)
        pool_mock = mocker.patch.object(db, "_pool")
        pool_mock.getconn.side_effect = [conn_morta, conn_saudavel]

        result = db._get_healthy_conn()

        assert result is conn_saudavel
        pool_mock.putconn.assert_called_once_with(conn_morta, close=True)

    def test_propaga_erro_quando_todas_as_tentativas_falham(self, mocker):
        conn_morta = _make_conn(
            mocker, cursor_execute_side_effect=psycopg2.OperationalError("server closed the connection unexpectedly")
        )
        pool_mock = mocker.patch.object(db, "_pool")
        pool_mock.getconn.return_value = conn_morta

        with pytest.raises(psycopg2.OperationalError):
            db._get_healthy_conn()

        assert pool_mock.getconn.call_count == db._POOL_MAXCONN
        assert pool_mock.putconn.call_count == db._POOL_MAXCONN


class TestGetDbConn:
    def test_commita_e_devolve_conexao_saudavel_ao_pool(self, mocker):
        conn = _make_conn(mocker)
        mocker.patch.object(db, "_get_healthy_conn", return_value=conn)
        pool_mock = mocker.patch.object(db, "_pool")

        with db.get_db_conn() as yielded:
            assert yielded is conn

        conn.commit.assert_called_once()
        pool_mock.putconn.assert_called_once_with(conn)

    def test_faz_rollback_e_devolve_conexao_ao_pool_em_erro_de_negocio(self, mocker):
        conn = _make_conn(mocker)
        conn.closed = 0
        mocker.patch.object(db, "_get_healthy_conn", return_value=conn)
        pool_mock = mocker.patch.object(db, "_pool")

        with pytest.raises(ValueError):
            with db.get_db_conn():
                raise ValueError("erro de negócio qualquer")

        conn.rollback.assert_called_once()
        pool_mock.putconn.assert_called_once_with(conn)

    def test_fecha_conexao_quebrada_em_vez_de_devolver_ao_pool(self, mocker):
        conn = _make_conn(mocker)
        conn.closed = 1
        mocker.patch.object(db, "_get_healthy_conn", return_value=conn)
        pool_mock = mocker.patch.object(db, "_pool")

        with pytest.raises(psycopg2.DatabaseError):
            with db.get_db_conn():
                raise psycopg2.DatabaseError("server closed the connection unexpectedly")

        conn.rollback.assert_not_called()
        pool_mock.putconn.assert_called_once_with(conn, close=True)
