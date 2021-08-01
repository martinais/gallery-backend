import redis
import os
import magic
import secrets
import json

from flask import Flask, jsonify, request, send_from_directory
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from werkzeug.utils import secure_filename

from model import migrate_database, connect, disconnect, User, Album
from mail import MailManager

app = Flask(__name__)
app.debug = True
app.config["PIN_EXPIRATION_DELTA"] = os.environ.get('PIN_EXPIRATION_DELTA')
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET_KEY')
app.config["MAILJET_API_KEY"] = os.environ.get('MAILJET_API_KEY')
app.config["MAILJET_API_SECRET"] = os.environ.get('MAILJET_API_SECRET')
app.config["UPLOAD_FOLDER"] = '/srv/data/pics/'

ALLOWED_MIMETYPES = ['image/png', 'image/jpeg']

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


def create_user(name, email):
    user = User(name=name, email=email)
    if user.exists():
        warning('user already exists')
        return None
    if not user.save():
        error('unable to create an user')
        return None
    return user


def create_album(name):
    album = Album(name=name)
    if album.exists():
        warning('album already exists')
        return None
    if not album.save():
        error('unable to create an album')
        return None
    return album


def file_upload():
    if 'file' not in request.files:
        warning('no file part')
        return None
    file = request.files['file']
    if file.filename == '':
        warning('no file selected')
        return None
    return file


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWLIST:
        prefix = 'Access-Control-Allow-'
        response.headers.add(prefix + 'Origin', origin)
        response.headers.add(prefix + 'Credentials', 'true')
        response.headers.add(prefix + 'Headers', 'Authorization')
        response.headers.add(prefix + 'Headers', 'Content-Type')
        response.headers.add(prefix + 'Methods', 'DELETE,PUT,PATCH')
    return response


@app.route('/')
def index():
    return "Martinade's API"


@app.route('/login', methods=['POST'])
def login():
    connect()
    name = request.json.get("name", None)
    response = ('', 204)
    if not User(name=name).exists():
        warning('Bad username or password.')
    else:
        pin = secrets.token_hex(4).upper()
        if not kvstore.set(pin, name):  # TODO : EXPIRE the pin code
            error('Unable to store pin code.')
            response = (jsonify(msg='Unable to store pin code.'), 500)
        else:
            kvstore.expire(pin, app.config['PIN_EXPIRATION_DELTA'])
        if not mailmanager.send_login_mail(User.get(User.name == name), pin):
            error('unable to send mail')
            response = ('Unable to send mail.', 500)
    disconnect()
    return response


@app.route('/signin', methods=['POST'])
def signin():
    response = '', 409
    connect()
    data = request.get_json()
    if create_user(data.get('name'), data.get('email')):
        response = '', 204
    disconnect()
    return response


@app.route('/token', methods=['POST'])
def token():
    data = request.get_json()
    name = kvstore.get(data['code'])
    kvstore.delete(data['code'])
    if name:
        access_token = create_access_token(identity=name.decode())
        return jsonify(access_token=access_token), 201
    return '', 401


@app.route('/config', methods=['GET', 'PUT'])
@jwt_required()
def config():
    connect()
    response = '', 204
    if request.method == 'GET':
        albums = []
        for a in Album.select():
            album = a.asdict()
            [album.pop(key) for key in ['count', 'preview', 'slug']]
            album['pics'] = Album.get(Album.slug == a.slug).pics
            albums.append(album)
        users = [user.asdict() for user in User.select()]
        response = {'users': users, 'albums': albums}
    elif request.method == 'PUT':
        file = file_upload()
        config = json.loads(file.read())
        for user in config['users']:
            create_user(user['name'], user['email'])
        for a in config['albums']:
            album = create_album(a['name'])
            album.add_pics(a['pics'])
    disconnect()
    return response


@app.route('/users', methods=['GET'])
@jwt_required()
def users():
    connect()
    return {'users': [user.name for user in User.select()]}
    disconnect()


@app.route('/albums', methods=['POST', 'GET'])
@jwt_required()
def albums():
    connect()
    if request.method == 'GET':
        response = jsonify([album.asdict() for album in Album.select()])
    elif request.method == 'POST':
        album_name = request.get_json().get('name')
        if not album_name:
            response = 'An album should have a name.', 400
        else:
            album = create_album(album_name)
            if album:
                response = jsonify(album.asdict()), 201
            else:
                response = 'Album probably exists already.', 400
    disconnect()
    return response


@app.route('/albums/<slug>', methods=['GET', 'DELETE'])
@jwt_required()
def album(slug):
    connect()
    if request.method == 'GET':
        response = Album.get(Album.slug == slug).asdict()
    if request.method == 'DELETE':
        if Album.get(Album.slug == slug).xremove(debug):
            response = '', 204
    disconnect()
    return response


@app.route('/albums/<slug>/pics', methods=['PATCH', 'GET'])
@jwt_required()
def ablum_pics(slug):
    response = '', 204
    if request.method == 'GET':
        response = jsonify(pics=Album.get(Album.slug == slug).pics)
    if request.method == 'PATCH':
        body = request.get_json()
        toadd = body.get('+')
        toremove = body.get('-')
        if toadd:
            Album.get(Album.slug == slug).add_pics(toadd)
        elif toremove:
            Album.get(Album.slug == slug).remove_pics(toremove)
        else:
            error("wrong key in request: " + body)
            response = 'A `+` or `-` key is missing', 400
    return response


@app.route('/pic/<filehash>', methods=['PUT', 'GET'])
@jwt_required()
def pic(filehash):
    # TODO : https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
    response = '', 204
    if request.method == 'GET':
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], filehash, as_attachment=True
        )
    if request.method == 'PUT':
        file = file_upload()
        if magic.from_buffer(file.read(2048), mime=True) in ALLOWED_MIMETYPES:
            file.seek(0)
            # TODO store this somewhere (in exif ?)
            #filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filehash))
    return response
