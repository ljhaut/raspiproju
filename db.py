import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model.ElecPrice import ElecPrice
from datetime import datetime
from model.Base import Base

from config import config

engine = create_engine(config['psql_uri'])
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def saveData():
    with open('data.json', 'r') as file:
        dupes = 0
        data = json.load(file)
        for f in data:
            for p in f['hinnat']:
                hour = int(p['position'])
                prevhour = 0 if hour == 1 else hour - 1
                p['position'] = '{:02d}-{:02d}'.format(prevhour, hour)

                spot = session.query(ElecPrice).filter_by(
                    price = float(p['price.amount']),
                    interval = p['position'],
                    date = datetime.strptime(f['pvm'], '%Y%m%d')
                ).first()
                if spot is None:
                    spot = ElecPrice(
                        price = float(p['price.amount']),
                        interval = p['position'],
                        date = datetime.strptime(f['pvm'], '%Y%m%d')
                    )
                    session.add(spot)
                    session.commit()
                    print(f['pvm'], 'stored')
                else:
                    dupes += 1
                
                
        print('Done saving, dupes:', dupes)