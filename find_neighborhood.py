import time
import requests
import pandas as pd


NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


def reverse_geocode(lat, lon):
    """
    Face reverse geocoding cu Nominatim (OpenStreetMap)
    și întoarce (neighbourhood, region/sector).
    """
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 18,
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": "proiect-facultate-imobiliare/1.0 (concat10@example.com)"
    }

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[GEO] Eroare request pentru {lat}, {lon}: {e}")
        return None, None

    data = resp.json()
    addr = data.get("address", {})

    # cartier / zonă
    neighborhood = (
        addr.get("neighbourhood")
        or addr.get("city_district")
        or addr.get("quarter")
        or addr.get("suburb")
    )

    # sector / regiune (ce pui tu în 'region')
    region = addr.get("suburb") or addr.get("city_district")

    return neighborhood, region


def main():
    input_file = "olx_bucuresti_imobiliare_metro.csv"
    output_file = "olx_bucuresti_imobiliare_enhanced.csv"

    df = pd.read_csv(input_file)

    # adăugăm coloane noi dacă nu există deja
    if "region" not in df.columns:
        df["region"] = None
    if "neighborhood_real" not in df.columns:
        df["neighborhood_real"] = None

    for idx, row in df.iterrows():
        lat = row.get("lat")
        lon = row.get("lon")

        if pd.isna(lat) or pd.isna(lon):
            continue

        print(f"[{idx}] Geocode pentru lat={lat}, lon={lon} ...")
        neigh, region = reverse_geocode(lat, lon)
        df.at[idx, "neighborhood_real"] = neigh
        if region:
            df.at[idx, "region"] = region

        # sleep mic ca să nu supărăm Nominatim
        time.sleep(1.2)

    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"[OK] Am salvat fisierul imbunatatit in {output_file}")


if __name__ == "__main__":
    main()
