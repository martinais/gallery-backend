import redis
import os
import secrets
from flask import Flask, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from model import migrate_database, connect, disconnect, User, Album
from mail import MailManager

app = Flask(__name__)
app.debug = True
# TODO configure expiration on JWT token
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY')
app.config["MAILJET_API_KEY"] = os.environ.get('MAILJET_API_KEY')
app.config["MAILJET_API_SECRET"] = os.environ.get('MAILJET_API_SECRET')

kvstore = redis.Redis(host='kvstore')

jwtmanager = JWTManager(app)
mailmanager = MailManager(app)

ALLOWLIST = ['http://localhost:8080', 'http://localhost:5000']


# TODO add calling function name before messages
def debug(msg):
    app.logger.debug(msg)


def warning(msg):
    app.logger.warning(msg)


def error(msg):
    app.logger.error(msg)


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWLIST:
        prefix = 'Access-Control-Allow-'
        response.headers.add(prefix + 'Origin', origin)
        response.headers.add(prefix + 'Credentials', 'true')
        response.headers.add(prefix + 'Headers', 'Authorization')
        response.headers.add(prefix + 'Headers', 'Content-Type')
    return response


@app.route('/')
def index():
    return "Martinade's API"


@app.route('/login', methods=['POST'])
def login():
    connect()
    name = request.json.get("name", None)
    if User.select().where(User.name == name).count() == 0:
        warning('Bad username or password.')
    else:
        pin = secrets.token_hex(4).upper()
        if not kvstore.set(pin, name):  # TODO : EXPIRE the pin code
            error('Unable to store pin code.')
            disconnect()
            return jsonify(msg='Unable to store pin code.'), 500
        mailmanager.send_login_mail(User.get(User.name == name), pin)
    disconnect()
    return '', 204


@app.route('/signin', methods=['POST'])
def signin():
    connect()
    data = request.get_json()
    # TODO : expect uniqueness of name from model and remove the next line
    if User.select().where(User.name == data.get('name')).count() == 0:
        if User(name=data.get('name'), email=data.get('email')).save():
            disconnect()
            return '', 204
        error('unable to create user')
    disconnect()
    return '', 409


@app.route('/token', methods=['POST'])
def token():
    data = request.get_json()
    name = kvstore.get(data['code'])  # TODO : DELETE the pin code
    if name:
        access_token = create_access_token(identity=name.decode())
        return jsonify(access_token=access_token), 201
    return '', 401


@app.route('/users', methods=['GET'])
@jwt_required()
def users():
    connect()
    users = [user.name for user in User.select()]
    return {'users': users}
    disconnect()


@app.route('/albums', methods=['POST', 'GET'])
@jwt_required()
def albums():
    connect()
    if request.method == 'GET':
        response = jsonify([album.asdict() for album in Album.select()])
    elif request.method == 'POST':
        data = request.get_json()
        album = Album(name=data.get('name'))
        # TODO : expect album uniqueness
        if not album.save():
            error('unable to create an album')
        response = jsonify(album.asdict()), 201
    disconnect()
    return response

@app.route('/albums/<slug>', methods=['GET'])
@jwt_required()
def album(slug):
    connect()
    if request.method == 'GET':
        response = Album.get(slug == slug).asdict()
    disconnect()
    return response
