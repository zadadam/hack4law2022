from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

import re

class Item(BaseModel):
    name: str
    description: Union[str, None] = None
    price: float
    tax: Union[float, None] = None

class Sad(BaseModel):
    nazwa: str
    adres: str
    konto: str
        
class Sprawa(BaseModel):
    miejscowosc: str
    opis_sprawy: str

class SprawaCena(BaseModel):
    typ_sprawy: str
    kwota: float
    sad: str
    konto: Union[str, None]
        
class Pozew(BaseModel):
    text: str
    analiza: Union[dict, None]
        
app = FastAPI()

sady = [
    ('SO', 'Krosno', 'Sąd Okręgowy w Krośnie', 'ul. Sienkiewicza 12, 38-400 Krosno', '94 1010 1528 0026 2622 3100 0000'),
    ('SR', 'Brzozowa', 'Sąd Rejonowy w Brzozowie', 'ul. 3 Maja 2A, 36-200 Brzozów', '94 1010 1528 0026 2622 3100 0000'),
    ('SR','Sanok','Sąd Rejonowy w Sanoku','ul. Kościuszki 5, 38-500 Sanok', '79 1010 1528 0030 6922 3100 0000'),
    ('SR', 'Lesko','Sąd Rejonowy w Lesku', 'ul. Plac Konstytucji 3-go Maja 9, 38-600 Lesko', '67 1010 1528 0012 7022 3100 0000' ),
    ('SR', 'Jasło','Sąd Rejonowy w Jaśle', 'ul. Armii Krajowej 3, 38-200 Jasło', '48 1010 1528 0035 0622 3100 0000'),
    ('SR', 'Krosno', 'Sąd Rejonowy w Krośnie', 'ul. Sienkiewicza 12, 38-400 Krosno', '44 1010 1528 0033 5922 3100 0000'),
    ('SR', 'Nowy Żmigród','Sąd Rejonowy w Jaśle', 'ul. Armii Krajowej 3, 38-200 Jasło', '48 1010 1528 0035 0622 3100 0000'),
]

sady_konta ={
    'Sąd Rejonowy w Jaśle' : '48 1010 1528 0035 0622 3100 0000',
}


sprawy = [
    ('o prawa niemajątkowe i łącznie z nimi dochodzone rozszczenia majątkowe', 'SO'),
    ('o roszczenia wynikające z Prawa prasowego', 'SO'),
    ('o prawa majątkowe', 'SO'),
    ('o wydanie orzeczenia zastępującego uchwałę o podziale spółdzielni', 'SO')
]


default_sprawy = 'SR'

@app.post("/items/")
async def create_item(item: Item):
    return item

@app.post('/wlasciwy_sad')
async def get_wlasciwy_sad(sprawa: Sprawa):
    sprawa_opis = sprawa.opis_sprawy[:10].lower()
    adres = sprawa.miejscowosc.lower()
    for typ in sprawy:
        if typ[0][:10] == sprawa_opis:
            return {
                'nazwa': sady[0][2],
                'adres': sady[0][3],
                'konto': sady[0][4]
            }
        
    for sad in sady:
        if adres.count(sad[1].lower()) > 0:
            return {
                'nazwa': sad[2],
                'adres': sad[3],
                'konto': sad[4]
            }
        
    return {
        'nazwa': sady[5][2],
        'adres': sady[5][3],
        'konto': sady[5][4]
    }

@app.post('/kwota-pozwu')
async def get_kwota(sprawa: SprawaCena):
    
    sad = sprawa.sad
    typ = sprawa.typ_sprawy
    kwota = sprawa.kwota
    if kwota == 0:
        kwota_out = 30
    else:
        kwota_out = float(int(kwota * 0.05))
    return {
        'typ_sprawy': typ,
        'konto': sady_konta.get(sad, '48 1010 1528 0035 0622 3100 0000'),
        'kwota': kwota_out
    }
        
    
def get_postawy_kpc(text):
    return re.findall(r'[aA]rt\.?[\s\w\d§]+k\.?p?\.?c\.?', text)

def get_postawy_inne(text):
    return re.findall(r'[aA]rt\.?[\s\w\d§\(\)\.ąęźćśńóĄĘŹĆŚŃÓ]+poz\.\s+\d+\)', text)

"""art. 13 ust. 2 ustawy z dnia 28 lipca 2005 r. o kosztach sądowych w sprawach cywilnych tj. z dnia 7 kwietnia 2022 r. (Dz.U. z 2022 r. poz. 1125)"""

def get_strony(text):
    paragraphs = text.replace(' \n', '\n').split("\n\n")
    paragraphs = list(filter(lambda x : x.strip() != '', paragraphs ))
    paragraphs

    pozwany = ''
    powod = ''
    reprezentacja =''

    for par in paragraphs:
        if par.lower().count('pozwany') > 0 and not pozwany:
            pozwany = par.replace('-Pozwany-','').strip()

        if par.lower().count('powód') > 0 and not powod:
            powod = par.replace('-Powód-','').strip()

        if par.lower().count('reprezentowany') > 0 and not reprezentacja:
            reprezentacja = par.strip()

    return {
        'pozwany': pozwany,
        'powód': powod, 
        'reprezentowany przez' :reprezentacja
    }

def remove_coma(x):
    x = x.strip()
    if x.endswith(','):
        x = x[:-1]
    if x.endswith('.'):
        x = x[:-1]
    if x.startswith('-'):
        x = x[1:].strip()
    return x 

def get_zalaczniki(text):
    
    paragraphs = text.replace(' \n', '\n').split("\n\n")
    paragraphs = list(filter(lambda x : x.strip() != '', paragraphs ))
    zalaczniki = []
    for ii, par in enumerate(paragraphs):
        if par.lower().count('załączniki') and par.count(':') and par.count('\n') > 3:
            zalaczniki = par.split('\n')
    zalaczniki = list(map(lambda x: remove_coma(x), filter(lambda x: x.strip() != '' and x.lower().count('załączniki') == 0, zalaczniki)))
    return zalaczniki

@app.post('/analiza')
async def get_analisys(pozew: Pozew):
    podstawy = get_postawy_kpc(pozew.text) + get_postawy_inne(pozew.text)
    return {
        'text':pozew.text,
        'analiza':{
            'podstawy': podstawy,
            'strony' : get_strony(pozew.text),
            'zalaczniki': get_zalaczniki(pozew.text)
        }
    }