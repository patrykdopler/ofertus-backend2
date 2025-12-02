import io
import base64
from fastapi import FastAPI, UploadFile, File, Form
from docxtpl import DocxTemplate, InlineImage
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from PIL import Image
from typing import List, Dict, Any
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------
#  NORMALIZACJA OBRAZÓW 4.7 CM x 4.7 CM
# -----------------------------------------
def make_inline_image(doc: DocxTemplate, image_bytes: bytes) -> InlineImage:
    image = Image.open(io.BytesIO(image_bytes))
    output = io.BytesIO()
    image.save(output, format="PNG")
    output.seek(0)

    return InlineImage(doc, output, width=docx_cm(4.7), height=docx_cm(4.7))


def docx_cm(value: float):
    from docx.shared import Cm
    return Cm(value)


# -----------------------------------------
#  NORMALIZACJA ITEMÓW
# -----------------------------------------
def normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []

    for idx, row in enumerate(items, start=1):
        nr = row.get("LP", idx)

        opis = row.get("OPIS", "")
        if opis is None:
            opis = ""

        ilosc = row.get("ILOSC", "")
        if ilosc is None:
            ilosc = ""

        nazwa = row.get("NAZWA_RYSUNEK", "")
        if nazwa is None:
            nazwa = ""

        foto = row.get("IMAGE", None)
        inline = None

        if foto and isinstance(foto, str) and foto.startswith("data:image"):
            try:
                head, data = foto.split(",", 1)
                decoded = base64.b64decode(data)
                inline = decoded
            except:
                inline = None

        normalized.append(
            {
                "row": nr,
                "OPIS": str(opis),
                "ILOSC": str(ilosc),
                "NAZWA_RYSUNEK": str(nazwa),
                "IMAGE": inline,  # bytes lub None
            }
        )

    return normalized


# -----------------------------------------
#  KONSTRUKCJA KONTEXTU DO DOCX
# -----------------------------------------
def build_context(data: Dict[str, Any]) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}

    ctx["DATA"] = data.get("data", "")
    ctx["NUMER_OFERTY"] = data.get("numer_oferty", "")

    # SYSTEMY – odporne na None / NaN / liczby
    systemy = data.get("systemy", [])
    ctx["SYSTEMY"] = [
        str(s).strip()
        for s in systemy
        if s is not None and str(s).strip()
    ]

    ctx["KOLOR"] = data.get("kolor", "")
    ctx["KWOTA_NETTO"] = data.get("kwota_netto", "")

    ctx["KLIENT_IMIE"] = data.get("klient_imie", "")
    ctx["KLIENT_EMAIL"] = data.get("klient_email", "")
    ctx["KLIENT_TEL"] = data.get("klient_tel", "")
    ctx["LOKALIZACJA_OBIEKTU"] = data.get("lokalizacja_obiektu", "")

    ctx["HANDLOWIEC_IMIE"] = data.get("handlowiec_imie", "")
    ctx["HANDLOWIEC_TEL"] = data.get("handlowiec_tel", "")
    ctx["HANDLOWIEC_MAIL"] = data.get("handlowiec_mail", "")

    # Pozycje
    items_raw = data.get("items", [])
    items = normalize_items(items_raw)

    ctx_items = []
    # wstawiamy obraz do InlineImage
    for row in items:
        imgbytes = row["IMAGE"]

        if imgbytes:
            try:
                inline = make_inline_image(DocxTemplate("template.docx"), imgbytes)
            except:
                inline = None
        else:
            inline = None

        ctx_items.append(
            {
                "LP": row["row"],
                "OPIS": row["OPIS"],
                "ILOSC": row["ILOSC"],
                "NAZWA_RYSUNEK": row["NAZWA_RYSUNEK"],
                "IMAGE": inline,
            }
        )

    ctx["items"] = ctx_items

    return ctx


# -----------------------------------------
#  FASTAPI – GENEROWANIE DOCX
# -----------------------------------------
class OfferModel(BaseModel):
    data: str = ""
    numer_oferty: str = ""
    systemy: list = []
    kolor: str = ""
    kwota_netto: str = ""
    klient_imie: str = ""
    klient_tel: str = ""
    klient_email: str = ""
    lokalizacja_obiektu: str = ""
    handlowiec_imie: str = ""
    handlowiec_tel: str = ""
    handlowiec_mail: str = ""
    items: list = []


@app.post("/generate-docx")
async def generate_docx(payload: OfferModel):
    try:
        doc = DocxTemplate("template.docx")
        ctx = build_context(payload.dict())

        doc.render(ctx)

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)

        return Response(
            content=output.read(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=oferta.docx"
            }
        )
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def root():
    return {"status": "OK"}
