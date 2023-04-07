import requests
import xmltodict
import json
import time
import socket
import threading

from datetime import datetime, timedelta
from config import config

api_key = config['api_key']
debug = config['debug']
HOST = 'localhost'
PORT = 8000

if debug == False:
    import RPi.GPIO as GPIO

def handleRequest(conn):
    request = conn.recv(1024).decode('utf-8')
    if 'GET /' in request:
        with open('data.json', 'r') as f:
            data = json.load(f)
            f.close()
        response = f'HTTP/1.1 200 OK\nContent-Type: application/json\n\n{data}'
        conn.sendall(response.encode('utf-8'))

def runServer():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Servu kuuntelee {HOST}:{PORT}')

        while True:
            conn, addr = s.accept()
            print(f'Yhdistetty {addr}')
            handleRequest(conn)
            conn.close()

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

#Alustetaan relekortti
def initGPIO():
    if debug == False:
        Relay = [5, 6, 13, 16, 19, 20, 21, 26]

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for i in range(0,8):
            GPIO.setup(Relay[i], GPIO.OUT)
            GPIO.output(Relay[i], GPIO.HIGH)

def main():

    initGPIO()

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
                            print("Rele päälle")
                            päällä = True
                            if debug == False:
                                try:
                                    GPIO.output(5, GPIO.LOW)
                                except:
                                    GPIO.cleanup()
                    else:
                        if päällä:
                            time.sleep(2)
                            print("Rele pois päältä")
                            päällä = False
                            if debug == False: GPIO.output(5, GPIO.HIGH)    

                    time.sleep(2)
    except:
        print("exit")
        if debug == False: GPIO.cleanup()

if __name__ == '__main__':
    server_thread = threading.Thread(target=runServer)
    server_thread.start()

    main()