from flask import Flask, request, jsonify

from src.config import Config
from src.db import init_db
from src.utils.errors import register_error_handlers
from src.utils.json_provider import AppJSONProvider
from src.routes.usuarios import usuarios_bp
from src.routes.comprovantes import comprovantes_bp
from src.routes.agendamentos import agendamentos_bp
from src.routes.listas import listas_bp
from src.routes.contas import contas_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.json = AppJSONProvider(app)

    @app.before_request
    def check_api_key():
        if Config.API_KEY is None:
            return  # auth desativada — API_KEY não definida (dev local)
        key = request.headers.get("X-API-Key")
        if not key or key != Config.API_KEY:
            return jsonify({"error": "unauthorized"}), 401

    init_db()
    register_error_handlers(app)

    app.register_blueprint(usuarios_bp)
    app.register_blueprint(comprovantes_bp)
    app.register_blueprint(agendamentos_bp)
    app.register_blueprint(listas_bp)
    app.register_blueprint(contas_bp)

    return app
