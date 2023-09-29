import requests
import xmltodict
import json
import time
import threading
import signal
import sys


from flask import Flask, jsonify
from datetime import datetime, timedelta
from config import config

api_key = config['api_key']
debug = config['debug']

if debug == False:
    from talker import Talker


app = Flask(__name__)

# Haetaan data Entso-E:n API-rajapinnasta HTTP GET - requestilla, saadaan xml muotoista dataa
# Parametreina aikaperiodi, jolta halutaan dataa
def getSPOT(today, tomorrow):

    payload = {'securityToken':api_key,'documentType':'A44','in_Domain':'10YFI-1--------U', 'out_Domain':'10YFI-1--------U',
    'periodStart': f'{today}0000','periodEnd':f'{tomorrow}0000'}

    r = requests.get('https://web-api.tp.entsoe.eu/api', params=payload)

    xml_string = r.content.decode('utf-8')

    xml_dict = xmltodict.parse(xml_string)
    
    return xml_dict



# Määritellään ja formatoidaan haluttavat päivämäärät oikein
def todayTomorrow():
    today = datetime.now().strftime('%Y%m%d')
    tomorrow = datetime.now() + timedelta(1)
    tomorrow = tomorrow.strftime('%Y%m%d')
    print("Tänään:", today, "Huominen:", tomorrow, '\n')
    return today, tomorrow



# Laskee ja esittää päivän sähköhinnan keskiarvon neljältä peräkkäiseltä tunnilta, sekä etsii niistä halvimman ja kalleimman arvon
# Parametrina lista hinnoista tietyltä päivältä
def keskiarvot(lista):
    keskiarvot = []

    for i in range(len(lista)-3):
        ka = (float(lista[i]['price.amount'])+float(lista[i+1]['price.amount'])+float(lista[i+2]['price.amount'])+float(lista[i+3]['price.amount'])) / 4
        tunnit = str(int(lista[i]['position'])-1) + '-' + str(int(lista[i+3]['position']))

        keskiarvot.append({'keskiarvo': ka, 'tunnit': tunnit})

    mi = min(keskiarvot, key=lambda x: float(x['keskiarvo']))
    ma = max(keskiarvot, key=lambda x: float(x['keskiarvo']))

    print("halvin keskiarvo:",mi,"kallein keskiarvo:", ma, '\n')



# Tallentaa arvot "data.json" tiedostoon
# Parametreina päivä ja sen päivän arvot
def tallennaArvot(lista, aika):

    tallennettava = {"pvm": aika, "hinnat": lista}

    with open("data.json") as f:
        file = json.load(f)
        f.close()

    if not any(d["pvm"] == aika for d in file):

        file.append(tallennettava)

        with open("data.json", "w", encoding="utf-8")as f:
            json.dump(file, f, ensure_ascii=False, indent=4)
            f.close()
        print("Tiedostoon tehty lisäys päivälle", aika, '\n')

    else:

        print("Päivällä", aika, "on jo olemassa listaus tiedostossa", '\n')
        return


# Palauttaa listan arvojen kolme halvinta tuntia
# tulos: palauttaa listan dictejä halvoista tunneista
# pos: palauttaa listan tunneista, jolloin halpaa
def halvimmat(lista):
    
    sort = sorted(lista, key=lambda x: float(x['price.amount']), reverse=False)
    
    tulos = [sort[0], sort[1], sort[2]]
    pos = [sort[0]['position'], sort[1]['position'], sort[2]['position']]
    print("Päivitetyt halvat tunnit", tulos, pos)

    return tulos, pos

def spotTodTom(spot):
    if len(spot["Publication_MarketDocument"]["TimeSeries"]) != 2:
        spotToday = spot["Publication_MarketDocument"]["TimeSeries"]["Period"]["Point"]
        spotTomorrow = None
        print(spotToday, '\n')
    else:
        spotToday = spot["Publication_MarketDocument"]["TimeSeries"][0]["Period"]["Point"]
        spotTomorrow = spot["Publication_MarketDocument"]["TimeSeries"][1]["Period"]["Point"]
        print(spotToday, '\n')
        print(spotTomorrow, '\n')

    return spotToday, spotTomorrow

if debug == False:
        talker1 = Talker('/dev/ttyACM0')
        talker2 = Talker('/dev/ttyACM1')

def cleanup(signal, frame):
        print("Cleaning up...")
        if not debug:
            talker1.send('clean()')
            talker2.send('clean()')
        sys.exit(0)

signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():

    päällä = False

    today, tomorrow = todayTomorrow()

    spot = getSPOT(today, tomorrow)
    
    spotToday, spotTomorrow = spotTodTom(spot)

    tallennaArvot(spotToday, today)
    if spotTomorrow != None:
        tallennaArvot(spotTomorrow, tomorrow)   

    halvat, halvpos = halvimmat(spotToday)

    try:
        while True:

            print("\n UUSI KIERROS \n")

            tunti = datetime.now() + timedelta(hours=1)
            tunti = tunti.replace(minute=0,second=0)
            pos = tunti.strftime("%H")
            tunti = tunti.strftime("%D|%H:%M:%S")

            if pos[0] == '0': 
                pos = pos[1:]

            if pos == '0':
                pos = '24'

            print("position:", pos)
            print("seuraava tunti:", tunti)
            print("aika nyt:", datetime.now().strftime("%D|%H:%M:%S"))
            print("halvat tunnit:", halvat, halvpos)

            if pos == '1':
                print("Päivä vaihtui")
                today, tomorrow = todayTomorrow()
                if spotTomorrow != None:
                    spotToday = spotTomorrow
                    spotTomorrow = None
                    halvat, halvpos = halvimmat(spotToday)

            if pos == '16':
                spot = getSPOT(today, tomorrow)

                spotToday, spotTomorrow = spotTodTom(spot)
                
                tallennaArvot(spotToday, today)
                if spotTomorrow != None:
                    tallennaArvot(spotTomorrow, tomorrow)

            if spotTomorrow == None and int(pos)>=19:
                print("Huomisen hintoja ei ole vielä saatu, etsitään...")
                spot = getSPOT(today, tomorrow)

                spotToday, spotTomorrow = spotTodTom(spot)
                
                tallennaArvot(spotToday, today)
                if spotTomorrow != None:
                    tallennaArvot(spotTomorrow, tomorrow)

            while datetime.now().strftime("%D|%H:%M:%S") < tunti:
                    
                # Jos tämän tunnin hinta on halvimpien joukossa, kytketään rele päälle
                if any(d == pos for d in halvpos):

                    if not päällä:
                        time.sleep(2)
                        päällä = True
                        if debug == False:
                            try:
                                talker1.send(f'relaysHigh()')
                                talker2.send(f'relaysHigh()')
                                time.sleep(12)
                                print(talker1.receive())
                                print(talker2.receive())
                            except:
                                talker1.send('clean()')
                                talker2.send('clean()')
                                time.sleep(12)
                                print(talker1.receive())
                                print(talker2.receive())
                else:
                    if päällä:
                        time.sleep(2)
                        päällä = False
                        if debug == False:
                            talker1.send(f'relaysLow()')
                            talker2.send(f'relaysLow()')
                            time.sleep(12)
                            print(talker1.receive())
                            print(talker2.receive())

                time.sleep(2)
    except:
        print("exit")
        if debug == False:
            talker1.send('clean()')
            talker2.send('clean()')

@app.route('/')
def index():
    with open('data.json', 'r') as f:
        data = json.load(f)
    return jsonify(data)

def run_flask():
    app.run(host='0.0.0.0', port=8000)

if __name__ == '__main__':
    
    thread = threading.Thread(target=run_flask)
    thread.daemon = True
    thread.start()

    main()