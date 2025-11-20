import time
import re
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# ========= CONFIG =========

BASE_URL = "https://www.olx.ro/imobiliare/bucuresti/?currency=EUR&page={page}"

START_PAGE = 1  # prima pagină de parcurs
END_PAGE = 600    # ultima pagină (modifică după nevoie)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7",
}


# ========= HELPERI TEHNICI (HTML STATIC) =========

def get_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def make_absolute_url(href: str) -> str:
    if href.startswith("//"):
        return "https:" + href
    if href.startswith("/"):
        return "https://www.olx.ro" + href
    return href


def extract_listing_urls_from_search(html: str):
    soup = BeautifulSoup(html, "html.parser")
    urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/d/oferta/" in href and "ID" in href:
            full = make_absolute_url(href)
            full = full.split("?")[0]
            urls.add(full)

    return sorted(urls)


# ========= SELENIUM: LAT / LON DIN GOOGLE MAPS =========

def create_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")  # dacă nu vrei fereastră
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    return driver


def get_lat_lon_with_selenium(driver, url: str):
    """
    Se uită doar după link-ul maps.google.com/maps?ll=LAT,LON
    (nu mai dăm click pe 'Vezi locația pe hartă').
    """
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    try:
        maps_link = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//a[contains(@href,'maps.google.com/maps')]")
            )
        )
        href = maps_link.get_attribute("href")
        href = unquote(href)
    except TimeoutException:
        print(f"[SELENIUM] Fara link de harta pentru {url}")
        return None, None

    m = re.search(r"[?&]ll=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", href)
    if not m:
        print(f"[SELENIUM] Nu am putut extrage ll=lat,lon din {href}")
        return None, None

    try:
        lat = float(m.group(1))
        lon = float(m.group(2))
        return lat, lon
    except ValueError:
        return None, None


# ========= PARSARE PAGINĂ DE DETALIU =========

def parse_detail_page(url: str) -> dict:
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(" ", strip=True).replace("\xa0", " ")

    # --- id numeric real (ID: 295144282) ---
    ad_id = None
    m_num = re.search(r"ID:\s*([0-9]+)", full_text)
    if m_num:
        ad_id = m_num.group(1)
    else:
        m_url = re.search(r"ID([A-Za-z0-9]+)\.html", url)
        if m_url:
            ad_id = m_url.group(1)

    # --- title = titlul anunțului (Inchiriez apartament ...) ---
    # div cu data-cy="offer_title"
    title_container = soup.find(attrs={"data-cy": "offer_title"}) \
        or soup.find(attrs={"data-testid": "offer_title"})
    if title_container:
        title = title_container.get_text(" ", strip=True)
    else:
        # fallback: orice <h4> care NU e în containerul de preț
        title = None
        for h in soup.find_all(["h4", "h3", "h2", "h1"]):
            parent_price = h.find_parent("div", attrs={"data-testid": "ad-price-container"})
            if parent_price:
                continue  # sărim peste preț
            title = h.get_text(" ", strip=True)
            if title:
                break

    # --- price_eur ---
    price_eur = None
    price_h3 = soup.select_one('div[data-testid="ad-price-container"] h3')
    if price_h3:
        raw = price_h3.get_text(strip=True).replace("\xa0", " ")
        m = re.search(r"(\d[\d\s]*)", raw)
        if m:
            num = m.group(1).replace(" ", "")
            try:
                price_eur = int(num)
            except ValueError:
                price_eur = None

    # --- city & neighborhood (sector) ---
    city = "Bucuresti"
    neighborhood = None

    loc_title_p = soup.find("p", string=lambda s: isinstance(s, str) and s.strip().lower() == "localitate")
    if loc_title_p:
        first_p = loc_title_p.find_next("p")
        second_p = first_p.find_next("p") if first_p else None

        for cand in [first_p, second_p]:
            if not cand:
                continue
            txt = cand.get_text(strip=True)
            if "Bucuresti" in txt:
                parts = [p.strip() for p in txt.split(",")]
                if parts:
                    city = parts[0]
                if len(parts) > 1:
                    neighborhood = parts[1]
                break

    # --- property_type extins ---
    property_type = None
    text_lower = full_text.lower()

    if "apartamente - garsoniere" in text_lower:
        property_type = "apartment"
    elif "case de vanzare" in text_lower or "case de inchiriat" in text_lower:
        property_type = "house"
    elif "terenuri" in text_lower:
        property_type = "land"
    elif ("spatiu comercial" in text_lower or "spațiu comercial" in text_lower or
          "spatii comerciale" in text_lower):
        property_type = "spatiu comercial"
    elif "garaj" in text_lower:
        property_type = "garaj"
    elif ("spatiu depozitare" in text_lower or "spațiu depozitare" in text_lower or
          "depozit" in text_lower or "hală" in text_lower or "hala" in text_lower):
        property_type = "spatiu depozitare"
    else:
        if title:
            tl = title.lower()
            if "garsonier" in tl or "apartament" in tl:
                property_type = "apartment"
            elif "casa" in tl or "vilă" in tl or "vila" in tl:
                property_type = "house"
            elif "teren" in tl or "lot" in tl:
                property_type = "land"
            elif "spatiu comercial" in tl or "spațiu comercial" in tl:
                property_type = "spatiu comercial"
            elif "garaj" in tl:
                property_type = "garaj"
            elif "depozit" in tl or "spatiu depozitare" in tl or "spațiu depozitare" in tl:
                property_type = "spatiu depozitare"

    # --- size_sqm ---
    size_sqm = None
    m = re.search(r"Suprafata\s+utila:\s*([\d,\.]+)", full_text, flags=re.IGNORECASE)
    if m:
        val = m.group(1).replace(".", "").replace(",", ".")
        try:
            size_sqm = float(val)
        except ValueError:
            size_sqm = None

    # --- rooms ---
    rooms = None
    m = re.search(r"(\d+)\s*camer", full_text, flags=re.IGNORECASE)
    if m:
        try:
            rooms = int(m.group(1))
        except ValueError:
            rooms = None

    # --- year_built ---
    year_built = None
    m = re.search(r"An constructie:\s*([0-9]{4})", full_text)
    if m:
        try:
            year_built = int(m.group(1))
        except ValueError:
            year_built = None

    # --- floor ---
    floor = None
    m = re.search(r"Etaj:\s*([0-9]+|Parter)", full_text, flags=re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if val.lower().startswith("parter"):
            floor = 0
        else:
            try:
                floor = int(val)
            except ValueError:
                floor = None

    max_floor = None

    # --- description: textul proprietarului ---
    description = ""
    desc_cont = soup.find("div", attrs={"data-cy": "ad_description"})
    if desc_cont:
        body_div = desc_cont.find("div", recursive=False)
        if body_div:
            description = body_div.get_text(" ", strip=True)

    if not description:
        desc_label = soup.find(string=lambda s: isinstance(s, str) and "Descriere" in s)
        if desc_label:
            container = desc_label.parent
            parts = []
            for s in container.find_all_next(string=True):
                t = s.strip()
                if not t:
                    continue
                if t.startswith("ID:"):
                    break
                parts.append(t)
            if parts:
                description = " ".join(parts)

    # --- deal_type: rent / sale / unknown ---
    text_for_type = f"{title or ''} {description or ''}".lower()

    rent_keywords = [
        "inchiriez", "închiriez", "inchiriere", "închiriere",
        "de inchiriat", "de închiriat",
        "in chirie", "în chirie",
        "chirie", "chirii",
    ]
    sale_keywords = [
        "vand", "vând",
        "vanzare", "vânzare",
        "de vanzare", "de vânzare",
        "pret vanzare", "preț vânzare",
        "se vinde" , "spre vânzare"
    ]

    deal_type = "unknown"
    if any(kw in text_for_type for kw in sale_keywords):
        deal_type = "sale"
    elif any(kw in text_for_type for kw in rent_keywords):
        deal_type = "rent"

    # --- parking / heating ---
    text_for_features = text_for_type

    parking = "unknown"
    if re.search(r"\b(parcare|loc de parcare|garaj)\b", text_for_features):
        parking = "yes"

    heating = "unknown"
    if "centrala" in text_for_features:
        heating = "central_heating"

    # --- dist_to_metro / park ---
    dist_to_metro_min = None
    dist_to_park_min = None

    m = re.search(r"(\d+)\s*min[^\.]{0,60}metrou", text_for_features, flags=re.IGNORECASE)
    if m:
        try:
            dist_to_metro_min = int(m.group(1))
        except ValueError:
            dist_to_metro_min = None

    m = re.search(r"(\d+)\s*min[^\.]{0,60}parc", text_for_features, flags=re.IGNORECASE)
    if m:
        try:
            dist_to_park_min = int(m.group(1))
        except ValueError:
            dist_to_park_min = None
    title_for_csv = deal_type  # 'rent' / 'sale' / 'unknown'
    return {
        "id": ad_id,
        "title": title_for_csv,
        "property_type": property_type,
        "price_eur": price_eur,
        "city": city,
        "neighborhood": neighborhood,
        "lat": None,
        "lon": None,
        "size_sqm": size_sqm,
        "rooms": rooms,
        "year_built": year_built,
        "floor": floor,
        "max_floor": max_floor,
        "parking": parking,
        "heating": heating,
        "dist_to_metro_min": dist_to_metro_min,
        "dist_to_park_min": dist_to_park_min,
        "description": description,
        "source_url": url,
    }


# ========= MAIN =========

def scrape_olx_bucuresti():
    all_rows = []
    seen_urls = set()

    driver = create_driver()

    try:
        for page in range(START_PAGE, END_PAGE + 1):
            search_url = BASE_URL.format(page=page)
            print(f"[INFO] Descarc pagina de cautare: {search_url}")
            try:
                html = get_html(search_url)
            except Exception as e:
                print(f"[WARN] Nu pot descarca pagina {page}: {e}")
                continue

            listing_urls = extract_listing_urls_from_search(html)
            print(f"[INFO] Gasit {len(listing_urls)} anunturi pe pagina {page}")

            for url in listing_urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                print(f"   -> Parsez {url}")
                try:
                    row = parse_detail_page(url)

                    lat, lon = get_lat_lon_with_selenium(driver, url)
                    row["lat"] = lat
                    row["lon"] = lon

                    all_rows.append(row)
                except Exception as e:
                    print(f"[WARN] Eroare la {url}: {e}")

                time.sleep(1.0)

            time.sleep(2.0)

    finally:
        driver.quit()

    if not all_rows:
        print("[INFO] Nu am obtinut niciun anunt.")
        return

    df = pd.DataFrame(all_rows)

    required_cols = [
        "id", "title", "property_type", "price_eur",
        "city", "neighborhood", "lat", "lon", "size_sqm", "rooms",
        "year_built", "floor", "max_floor", "parking", "heating",
        "dist_to_metro_min", "dist_to_park_min", "description",
        "source_url",
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    df = df[required_cols]

    output_file = "olx_bucuresti_imobiliare.csv"
    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"[OK] Am salvat {len(df)} randuri in {output_file}")


if __name__ == "__main__":
    scrape_olx_bucuresti()
