from flask import jsonify

def fail(code: str, detail: str | None = None, status_code: int = 400):
    payload = {}
    payload["error"] = code
    
    if detail:
        payload["detail"] = detail
    
    return jsonify(payload), status_code

def ok(status_code: int = 204, data = None):
    if status_code == 204 or data is None:
        return "", status_code
    
    return jsonify(data), status_code
    