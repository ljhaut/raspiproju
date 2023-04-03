# L-mminvesivaraaja

Haetaan netistä sähkön SPOT-hinta seuraavalle päivälle ja sen mukaan tehdään erilaisia ratkaisuja ja toimintoja.

Tällä hetkellä ohjelma ohjaa releitä, jotka kytketään lämminvesivaraajaan ja sitä kautta kytkee sähkövirran päälle tai pois. 
Tulevaisuudessa toiminnallisuutta tullaan lisäämään.

Ohjelman toimimeksi täytyy luoda "config.py" tiedosto repon juureen. 

Tiedostoon tulee lisätä seuraava:

config = {
    'debug': False,
    'api_key':'oma avain tähän'
}

api_key on siis Entso E rajapinnassa käytettävä avain