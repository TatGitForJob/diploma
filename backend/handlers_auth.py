from flask import request, jsonify
from auth import VALID_CREDENTIALS

def register_routes_auth(app):
    @app.route("/login", methods=["POST"])
    def login():
        data = request.get_json()
        city = data.get("city")
        password = data.get("password")

        city_data = VALID_CREDENTIALS.get(city)
        if not city_data or city_data["password"] != password:
            return jsonify({"success": False, "error": "Неверный логин или пароль"}), 401

        return jsonify({
            "success": True,
            "label": city_data["label"]
        })
