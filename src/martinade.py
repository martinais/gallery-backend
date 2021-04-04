import os
from flask import Flask, jsonify, request
from model import User, migrate_database, connect, disconnect
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

app = Flask(__name__)
app.debug = True
app.config["JWT_SECRET_KEY"] = "super-secret"  # TODO: Change this!
jwt = JWTManager(app)


# === CORS ===
#
#ALLOWLIST = ['http://localhost:8080','http://localhost:5000']
#
# @app.after_request
# def add_cors_headers(response):
#    origin = request.headers.get('Origin')
#    if origin in ALLOWLIST:
#        response.headers.add('Access-Control-Allow-Origin', origin)
#        response.headers.add('Access-Control-Allow-Credentials', 'true')
#        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
#        response.headers.add('Access-Control-Allow-Headers', 'Cache-Control')
#        response.headers.add('Access-Control-Allow-Headers', 'X-Requested-With')
#        response.headers.add('Access-Control-Allow-Headers', 'Authorization')
#        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
#    return response
#
# ============


def debug(msg):
    app.logger.debug(msg)


def error(msg):
    app.logger.error(msg)


@app.route('/')
def index():
    return "Martinade's API"


@app.route('/login', methods=['POST'])
def login():
    name = request.json.get("name", None)
    if User.select().where(User.name == name).count() == 0:
        return jsonify({"msg": "Bad username or password"}), 401
    access_token = create_access_token(identity=name)
    return jsonify(access_token=access_token), 201


@app.route('/users', methods=['GET', 'POST'])
def users():
    connect()
    if request.method == 'GET':
        users = [user.name for user in User.select()]
        return {'users': users}
    elif request.method == 'POST':
        data = request.get_json()
        if User.select().where(User.name == data.get('name')).count() == 0:
            if User(name=data.get('name'), email=data.get('email')).save():
                return '', 204
            error('unable to create user')
        return '', 409
    disconnect()
