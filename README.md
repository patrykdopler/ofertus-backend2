
# Ofertus Backend v3 – z obsługą zdjęć pozycji

- FastAPI + docxtpl
- generuje DOCX na podstawie JSON (payload)
- obsługuje listę items z obrazkami w base64

## Dane wejściowe (payload)

```json
{
  "data": "26.11.2025",
  "numer_oferty": "",
  "systemy": ["AS 75", "AS 178HS"],
  "kolor": "",
  "kwota_netto": "",
  "klient_imie": "",
  "klient_email": "",
  "klient_tel": "",
  "lokalizacja_obiektu": "",
  "handlowiec_imie": "",
  "handlowiec_tel": "",
  "handlowiec_mail": "",
  "items": [
    {
      "lp": 1,
      "nazwa_rysunek": "Poz. 1 MB-78EI Witryny ...",
      "ilosc": "X4",
      "opis": "Wypełnienia: ...",
      "image_base64": "data:image/png;base64,AAAA..."
    }
  ]
}
```

W szablonie w tabeli należy użyć np.:

```jinja2
{% for row in items %}
  {{ row.LP }}
  {{ row.IMAGE }}
  {{ row.ILOSC }}
  {{ row.OPIS }}
{% endfor %}
```

Backend automatycznie zamieni `image_base64` na obrazek wstawiony do komórki (ok. 70 mm szerokości).
