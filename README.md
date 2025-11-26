
# Ofertus Backend v2 (FastAPI) – DOPLER szablon

Backend generuje ofertę dokładnie pod szablon `Oferta_SZABLON4.docx`.

## Struktura

- `main.py` – backend FastAPI
- `requirements.txt` – zależności
- `templates/oferta_template.docx` – Twój szablon Oferty DOPLER
- `generated/` – tu wpadają wygenerowane oferty

## Uruchomienie

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

API: `http://localhost:8000`

## Endpointy

### 1. GET /health

Prosty healthcheck.

### 2. POST /generate-docx

`multipart/form-data`

- pole `payload` – string z JSON
- opcjonalnie `template_file` – własny szablon `.docx`

Przykładowy JSON (payload):

```json
{
  "data": "21.11.2025",
  "miasto": "Częstochowa",
  "numer_oferty": "186112025",
  "klient_imie": "Bartosz Betka",
  "klient_email": "zofpol@onet.pl",
  "klient_tel": "514 168 484",
  "lokalizacja_obiektu": "Częstochowie",
  "systemy": [
    "AS 75 + AS 75P - okna i witryny drzwiowe",
    "AS 178HS - drzwi podnoszono-przesuwne z częścią stałą",
    "AS VGB - balustrady"
  ],
  "kolor": "RAL 7016 - struktura",
  "kwota_netto": "55.000,00 zł",
  "handlowiec_imie": "Patryk Stępień",
  "handlowiec_tel": "517 856 952",
  "handlowiec_mail": "patryk@dopler.com.pl",
  "items": [
    {
      "lp": 1,
      "nazwa_rysunek": "Poz. OZ 1  AS 75 + AS 75P - okna i witryny drzwiowe (B=2 100, H=850)",
      "ilosc": "X1",
      "opis": "Wypełnienia:\n4/18/4/18/4\n\nWyposażenie:\n- klamka w kolorze konstrukcji"
    }
  ]
}
```

### 3. POST /preview-context

`multipart/form-data`

- `payload` – jak wyżej

Zwraca JSON z contextem przekazywanym do szablonu (do debugowania).

## Szablon Word

W folderze `templates` znajduje się `oferta_template.docx`, który jest kopią Twojego `Oferta_SZABLON4.docx`.
Możesz go edytować w Wordzie i używać placeholderów docxtpl, np.:

- `{{data}}`
- `{{NUMER_OFERTY}}`
- `{{SYSTEM1}}` ... `{{SYSTEM5}}`
- `{{KOLOR}}`
- ew. dodatkowe:
  - `{{KWOTA_NETTO}}`
  - `{{KLIENT_IMIE}}`, `{{KLIENT_EMAIL}}`, `{{KLIENT_TEL}}`
  - `{{LOKALIZACJA_OBIEKTU}}`
  - `{{HANDLOWIEC_IMIE}}`, `{{HANDLOWIEC_TEL}}`, `{{HANDLOWIEC_MAIL}}`

Dla tabeli pozycji zalecany układ w szablonie:

```jinja2
{% for row in items %}
{{ row.LP }}
{{ row.NAZWA_RYSUNEK }}
{{ row.ILOSC }}
{{ row.OPIS }}
{% endfor %}
```

Backend przekazuje każdą pozycję z polami:
`lp`, `LP`, `nazwa_rysunek`, `NAZWA_RYSUNEK`, `ilosc`, `ILOSC`, `opis`, `OPIS`.
