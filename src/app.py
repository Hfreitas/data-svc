from flask import Flask

from src.db import init_db
from src.utils.errors import register_error_handlers
from src.routes.usuarios import usuarios_bp
from src.routes.comprovantes import comprovantes_bp
from src.routes.agendamentos import agendamentos_bp
from src.routes.listas import listas_bp
from src.routes.contas import contas_bp


def create_app() -> Flask:
    app = Flask(__name__)

    init_db()
    register_error_handlers(app)

    app.register_blueprint(usuarios_bp)
    app.register_blueprint(comprovantes_bp)
    app.register_blueprint(agendamentos_bp)
    app.register_blueprint(listas_bp)
    app.register_blueprint(contas_bp)

    return app
