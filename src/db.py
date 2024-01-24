import json
import bcrypt

from flask import Flask, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from entity.ElecPrice import ElecPrice
from entity.User import User
from entity.Base import Base

from config import config

app = Flask(__name__)

engine = create_engine(config['psql_uri'])
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

@app.route('/register', methods=['POST'])
def register():
    session = Session()

    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
    
    existingUser = session.query(User).filter_by(
        username = username
    ).first()
    if existingUser:
        return jsonify({'error': 'Username alreadu exists'}), 409
    
    hashedPassword = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    newUser = User(username = username, password = hashedPassword)
    session.add(newUser)
    session.commit()
    session.close()

    return jsonify({'message' : 'User created successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    session = Session()

    username = request.json.get('username')
    password = request.json.get('password')

    if not username or not password:
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = session.query(User).filter_by(
        username = username
    ).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
        
        return jsonify({'message': 'Login successful'}), 200
    
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

def saveData():
    session = Session()

    with open('../data.json', 'r') as file:

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

def run_app():
    app.run()