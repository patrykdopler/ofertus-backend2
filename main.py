
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from uuid import uuid4
import os
import json
import base64
from typing import Optional, List, Dict, Any

app = FastAPI(title="Ofertus Backend v3", version="3.0.0")

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


def normalize_items(data_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for itm in data_items:
        lp = itm.get("lp") or itm.get("LP") or itm.get("number") or ""
        nazwa = (
            itm.get("nazwa_rysunek")
            or itm.get("NAZWA_RYSUNEK")
            or itm.get("name")
            or ""
        )
        ilosc = itm.get("ilosc") or itm.get("ILOSC") or itm.get("qty") or ""
        opis = itm.get("opis") or itm.get("OPIS") or itm.get("fill") or ""

        row = {
            "lp": lp,
            "LP": lp,
            "nazwa_rysunek": nazwa,
            "NAZWA_RYSUNEK": nazwa,
            "ilosc": ilosc,
            "ILOSC": ilosc,
            "opis": opis,
            "OPIS": opis,
            "IMAGE": None,  # uzupełniamy później
        }

        img_b64 = itm.get("image_base64") or itm.get("image") or ""
        row["_image_base64"] = img_b64

        normalized.append(row)
    return normalized


def build_context(data: Dict[str, Any]) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}

    # Podstawowe pola – większość może być pusta
    ctx["data"] = data.get("data", "")
    ctx["DATA"] = ctx["data"]
    ctx["NUMER_OFERTY"] = data.get("numer_oferty", "")

    systemy: List[str] = data.get("systemy", [])
    for i in range(5):
        key = f"SYSTEM{i+1}"
        ctx[key] = systemy[i] if i < len(systemy) else ""

    ctx["KOLOR"] = data.get("kolor", "")
    ctx["KWOTA_NETTO"] = data.get("kwota_netto", "")

    ctx["KLIENT_IMIE"] = data.get("klient_imie", "")
    ctx["KLIENT_EMAIL"] = data.get("klient_email", "")
    ctx["KLIENT_TEL"] = data.get("klient_tel", "")

    ctx["LOKALIZACJA_OBIEKTU"] = data.get("lokalizacja_obiektu", "")

    ctx["HANDLOWIEC_IMIE"] = data.get("handlowiec_imie", "")
    ctx["HANDLOWIEC_TEL"] = data.get("handlowiec_tel", "")
    ctx["HANDLOWIEC_MAIL"] = data.get("handlowiec_mail", "")

    data_items: List[Dict[str, Any]] = data.get("items", [])
    ctx["items"] = normalize_items(data_items)

    return ctx


def inject_images(doc: DocxTemplate, ctx: Dict[str, Any]) -> None:
    items: List[Dict[str, Any]] = ctx.get("items", [])
    if not items:
        return

    for row in items:
        img_b64 = row.get("_image_base64") or ""
        if not img_b64:
            row["IMAGE"] = ""
            continue

        if "," in img_b64:
            _, b64data = img_b64.split(",", 1)
        else:
            b64data = img_b64

        try:
            img_bytes = base64.b64decode(b64data)
        except Exception:
            row["IMAGE"] = ""
            continue

        tmp_name = f"_img_{uuid4().hex}.png"
        tmp_path = os.path.join(OUTPUT_DIR, tmp_name)
        try:
            with open(tmp_path, "wb") as f:
                f.write(img_bytes)
            row["IMAGE"] = InlineImage(doc, tmp_path, width=Mm(70))
        except Exception:
            row["IMAGE"] = ""


@app.post("/generate-docx")
async def generate_docx(
    payload: str = Form(..., description="JSON z danymi oferty (Ofertuś)"),
    template_file: Optional[UploadFile] = File(
        None, description="Opcjonalny szablon .docx (docxtpl)"
    ),
):
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Niepoprawny JSON: {e}")

    if template_file is not None:
        temp_template_path = os.path.join(TEMPLATES_DIR, f"uploaded_{uuid4().hex}.docx")
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

    ctx = build_context(data)
    inject_images(doc, ctx)

    try:
        doc.render(ctx)
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
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Niepoprawny JSON: {e}")

    ctx = build_context(data)
    return JSONResponse(ctx)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
