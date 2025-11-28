import requests
import time
import pandas as pd

def reverse_geocode(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1
    }
    resp = requests.get(url, params=params, headers={"User-Agent": "tolu-conecta/1.0"})
    if resp.status_code == 200:
        data = resp.json()
        address = data.get("address", {})
        return {
            "barrio_osm": address.get("suburb") or address.get("neighbourhood"),
            "municipio_osm": address.get("town") or address.get("city"),
            "departamento_osm": address.get("state")
        }
    return {"barrio_osm": None, "municipio_osm": None, "departamento_osm": None}

catalogo = pd.read_csv("data/catalogo.csv")

enriquecidos = []
for idx, fila in catalogo.iterrows():
    info = reverse_geocode(fila["LATITUD"], fila["LONGITUD"])
    enr = {**fila.to_dict(), **info}
    enriquecidos.append(enr)
    time.sleep(1)  # MUY IMPORTANTE: respetar el límite de la API

df_enriquecido = pd.DataFrame(enriquecidos)
df_enriquecido.to_csv("data/catalogo_enriquecido.csv", index=False)
