import pandas as pd
import json
from geopy.distance import geodesic
#Citim
with open("metrodata.json", "r", encoding="utf-8") as f:
    data = json.load(f)
#Normalizam
df = pd.json_normalize(data["elements"])

#Selectam ce ne trebuie:
df = df[["lat", "lon", "tags.name"]]

df.to_csv("metro.csv", index=False) #am convertit si salvat csv

data = pd.read_csv("olx_bucuresti_imobiliare_enhanced.csv")
metro = pd.read_csv("metro.csv")

def timp_metro(lat,lon):
    locatie = (lat, lon)
    distante = metro.apply(lambda row: geodesic(locatie, (row['lat'], row['lon'])).km, axis=1)
    metro_aproape = distante.min()
    km_h = 12
    timp_min = (metro_aproape / km_h) * 60
    return round(timp_min, 1)

data['dist_to_metro_min'] = data.apply(lambda row: timp_metro(row['lat'], row['lon']), axis=1)

data.to_csv("olx_bucuresti_imobiliare_metro.csv", index=False)


