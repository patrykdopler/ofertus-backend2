
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from docxtpl import DocxTemplate
from uuid import uuid4
import os
import json
from typing import Optional, List, Dict, Any

app = FastAPI(title="Ofertus Backend v2", version="2.0.0")

# CORS – dopasuj w razie potrzeby
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "generated")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEFAULT_TEMPLATE = os.path.join(TEMPLATES_DIR, "oferta_template.docx")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def build_context(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Buduje context dokładnie pod szablon Oferty DOPLER.
    """
    # Dane podstawowe
    context: Dict[str, Any] = {}

    # Data / miasto / numer oferty
    context["data"] = data.get("data", "")  # {{data}} w szablonie
    context["DATA"] = context["data"]       # na wszelki wypadek duże litery

    context["NUMER_OFERTY"] = data.get("numer_oferty", "")  # {{NUMER_OFERTY}}

    # Systemy – mapowane na {{SYSTEM1}}–{{SYSTEM5}}
    systemy: List[str] = data.get("systemy", [])
    for i in range(5):
        key = f"SYSTEM{i+1}"
        context[key] = systemy[i] if i < len(systemy) else ""

    # Kolor – {{KOLOR}}
    context["KOLOR"] = data.get("kolor", "")

    # Kwota netto – jeśli wstawisz placeholder w szablonie, np. {{KWOTA_NETTO}}
    context["KWOTA_NETTO"] = data.get("kwota_netto", "")

    # Dane klienta – jeśli dodasz te placeholdery w szablonie:
    context["KLIENT_IMIE"] = data.get("klient_imie", "")
    context["KLIENT_EMAIL"] = data.get("klient_email", "")
    context["KLIENT_TEL"] = data.get("klient_tel", "")

    # Lokalizacja obiektu – jeśli dodasz np. {{LOKALIZACJA_OBIEKTU}}
    context["LOKALIZACJA_OBIEKTU"] = data.get("lokalizacja_obiektu", "")

    # Handlowiec – jeśli dodasz placeholdery:
    context["HANDLOWIEC_IMIE"] = data.get("handlowiec_imie", "")
    context["HANDLOWIEC_TEL"] = data.get("handlowiec_tel", "")
    context["HANDLOWIEC_MAIL"] = data.get("handlowiec_mail", "")

    # Tabela pozycji
    items: List[Dict[str, Any]] = data.get("items", [])

    # Dla maksymalnej kompatybilności:
    # - przekazujemy listę "items"
    # - każdy element ma pola w dwóch wersjach: duże i małe litery
    normalized_items: List[Dict[str, Any]] = []
    for itm in items:
        lp = itm.get("lp") or itm.get("LP") or ""
        nazwa = itm.get("nazwa_rysunek") or itm.get("NAZWA_RYSUNEK") or ""
        ilosc = itm.get("ilosc") or itm.get("ILOSC") or ""
        opis = itm.get("opis") or itm.get("OPIS") or ""

        row = {
            "lp": lp,
            "LP": lp,
            "nazwa_rysunek": nazwa,
            "NAZWA_RYSUNEK": nazwa,
            "ilosc": ilosc,
            "ILOSC": ilosc,
            "opis": opis,
            "OPIS": opis,
        }
        normalized_items.append(row)

    context["items"] = normalized_items

    return context


@app.post("/generate-docx")
async def generate_docx(
    payload: str = Form(..., description="JSON z danymi oferty (Ofertuś)"),
    template_file: Optional[UploadFile] = File(
        None, description="Opcjonalny szablon .docx (docxtpl)"
    ),
):
    """
    Oczekiwany payload (JSON jako string w polu 'payload').

    Przykład:

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
          "nazwa_rysunek": "Poz. OZ 1  AS 75 + AS 75P ... (B=2 100, H=850)",
          "ilosc": "X1",
          "opis": "Wypełnienia:\\n4/18/4/18/4\\n\\nWyposażenie:\\n- klamka w kolorze konstrukcji"
        }
      ]
    }
    """
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Niepoprawny JSON: {e}")

    # wybór szablonu
    if template_file is not None:
        temp_template_path = os.path.join(
            TEMPLATES_DIR, f"uploaded_{uuid4().hex}.docx"
        )
        contents = await template_file.read()
        with open(temp_template_path, "wb") as f:
            f.write(contents)
        template_path = temp_template_path
    else:
        if not os.path.exists(DEFAULT_TEMPLATE):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Brak domyślnego szablonu 'oferta_template.docx' w folderze 'templates'. "
                    "Dodaj tam swój szablon lub wyślij go w polu 'template_file'."
                ),
            )
        template_path = DEFAULT_TEMPLATE

    try:
        doc = DocxTemplate(template_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd ładowania szablonu: {e}")

    # context dokładnie pod ofertę
    context = build_context(data)

    try:
        doc.render(context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd renderowania szablonu: {e}")

    out_name = f"oferta_{uuid4().hex}.docx"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    try:
        doc.save(out_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd zapisu pliku: {e}")

    return FileResponse(
        out_path,
        filename=out_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.post("/preview-context")
async def preview_context(payload: str = Form(...)):
    """
    Endpoint pomocniczy – zwraca context, który idzie do szablonu.
    """
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Niepoprawny JSON: {e}")

    context = build_context(data)
    return JSONResponse(context)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
