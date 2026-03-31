from flask import Flask
from src.utils.api_response import fail


def register_error_handlers(app: Flask):
    @app.errorhandler(400)
    def bad_request(e):
        return fail("bad_request", str(e), 400)

    @app.errorhandler(404)
    def not_found(e):
        return fail("not_found", status_code=404)

    @app.errorhandler(422)
    def unprocessable(e):
        return fail("unprocessable_entity", str(e), 422)

    @app.errorhandler(500)
    def internal_error(e):
        return fail("internal_server_error", status_code=500)
