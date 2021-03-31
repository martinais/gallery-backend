import os
from flask import Flask, jsonify, request
from model import User, migrate_database, connect, disconnect

app = Flask(__name__)
app.debug = True
migrate_database()

# === CORS ===
# 
#ALLOWLIST = ['http://localhost:8080','http://localhost:5000']
#
#@app.after_request
#def add_cors_headers(response):
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


@app.route('/users', methods=['PUT', 'GET'])
def users():
    connect()
    users = [user.name for user in User.select()]
    debug(User.select())
    disconnect()
    return jsonify(users)
