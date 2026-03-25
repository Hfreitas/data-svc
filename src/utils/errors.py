from flask import Flask, jsonify


def register_error_handlers(app: Flask):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "bad_request", "detail": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({"error": "unprocessable_entity", "detail": str(e)}), 422

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "internal_server_error"}), 500
