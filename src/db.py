import bcrypt
import json
import jwt
import os 

from flask import Flask, jsonify, make_response, request
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from entity.ElecPrice import ElecPrice
from entity.User import User
from entity.Base import Base

from dotenv import dotenv_values

if os.getenv('ENVIRONMENT') == 'docker':
    config = dotenv_values('.env.docker')
else:
    config = dotenv_values('.env.local')

app = Flask(__name__)
CORS(app, origins=["*"], supports_credentials=True)

engine = create_engine(config['PSQL_URL'])
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@app.route('/register', methods=['POST'])
def register():
    session = Session()
    try:
        username = request.json.get('username')
        password = request.json.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400
        
        existingUser = session.query(User).filter_by(
            username = username
        ).first()
        if existingUser:
            return jsonify({'error': 'Username already exists'}), 409
        
        hashedPassword = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        newUser = User(username = username, password = hashedPassword, access = 'user')
        session.add(newUser)
        session.commit()

        return jsonify({'message' : 'User created successfully'}), 201
    finally:
        session.close()

@app.route('/login', methods=['POST'])
def login():
    session = Session()

    try:
        username = request.json.get('username')
        password = request.json.get('password')

        if not username or not password:
            return jsonify({'error': 'Missing username or password'}), 400
        
        user = session.query(User).filter_by(
            username = username
        ).first()
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):

            accessToken = createAccessToken(user)
            
            refreshToken = createRefreshToken(user)

            response = make_response(jsonify({'accessToken': accessToken}))

            response.set_cookie('refresh', refreshToken, httponly=True, expires=datetime.utcnow() + timedelta(days=7), samesite='None', secure=True)

            return response
        
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
        
    finally:
        session.close()

@app.route('/logout', methods=['POST'])
def logout():

    response = make_response(jsonify({'message':'Logged out succesfully'}))
    response.delete_cookie('refresh')

    return response

@app.route('/refresh_token', methods=['POST'])
def refresh():
    session = Session()

    try:
        refreshToken = request.cookies.get('refresh')

        try:
            data = jwt.decode(refreshToken, config['REFRESH_SECRET'], algorithms=['HS256'])

            user = session.query(User).filter_by(
            id = data['user.id']
            ).first()

            newAccessToken = createAccessToken(user)

            newRefreshToken = createRefreshToken(user)
            
            response = make_response(jsonify({'accessToken': newAccessToken}))
            response.set_cookie('refresh', newRefreshToken, httponly=True, expires=datetime.utcnow() + timedelta(days=7), samesite='None', secure=True)

            return response

        except jwt.ExpiredSignatureError:
            return jsonify({'error', 'Refresh token expired'}), 401
        except:
            return jsonify({'error': 'Invalid token'}), 400
    finally:
        session.close()

@app.route('/logs')
def get_logs():
    log_file = 'app.log'
    if os.path.exists(log_file):
        with open(log_file, 'r') as file:
            lines = file.readlines()[-200:]
            return jsonify(lines)
    else:
        return jsonify([])

def saveData():
    session = Session()

    with open('data.json', 'r') as file:

        dupes = 0
        data = json.load(file)

        for f in data:
            for p in f['hinnat']:

                hour = int(p['position'])
                prevhour = 0 if hour == 1 else hour - 1
                p['position'] = '{:02d}-{:02d}'.format(prevhour, hour)

                spot = session.query(ElecPrice).filter_by(
                    price=float(p['price.amount']),
                    interval=p['position'],
                    date=datetime.strptime(f['pvm'], '%Y%m%d')
                ).first()

                if spot is None:
                    spot = ElecPrice(
                        price=float(p['price.amount']),
                        interval=p['position'],
                        date=datetime.strptime(f['pvm'], '%Y%m%d')
                    )
                    session.add(spot)
                    session.commit()
                    print(f['pvm'], 'stored')
                else:
                    dupes += 1

        session.close()
        return f'Data saved, dubes: {dupes}'

def createAccessToken(user):
    with open('private.key', 'r') as f:
        privateKey = f.read()
        f.close()

    token = jwt.encode({
                'user.id': user.id,
                'user.access': user.access,
                'exp': datetime.utcnow() + timedelta(minutes=15),
                "https://hasura.io/jwt/claims": {
                    "x-hasura-allowed-roles": [user.access],
                    "x-hasura-default-role": user.access,
                    'x-hasura-user-id': str(user.id)
                }
            }, privateKey, algorithm='RS512')

    return token 

def createRefreshToken(user):

    token = jwt.encode({
                'user.id': user.id,
                'exp': datetime.utcnow() + timedelta(days=7)
            }, config['REFRESH_SECRET'], algorithm='HS256')

    return token 

def run_app():
    app.run(host='0.0.0.0', port=int(config['PORT']))