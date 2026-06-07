"""File serving, bbox, export (GeoTIFF/PNG/CSV/PDF), and anomalies endpoints."""
import io
import json
import zipfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fpdf import FPDF
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import AnomalyZone, Field, Flight, IndexMap
from app.schemas.schemas import IndexRecommendation

router = APIRouter(prefix="/flights", tags=["files"])

_FILE_MAP = {
    "orthophoto_preview": ("orthophoto_preview.png", "image/png"),
    "ndvi":               ("ndvi_preview.png", "image/png"),
    "ndre":               ("ndre_preview.png", "image/png"),
    "evi":                ("evi_preview.png",  "image/png"),
    "dsm":                ("dsm_preview.png",  "image/png"),
}


def _results_dir(flight_id: str) -> Path:
    return Path(settings.data_dir) / "flights" / flight_id / "results"


# ── bbox must be defined BEFORE the {file_type} catch-all ─────────────────────
@router.get("/{flight_id}/files/orthophoto/bbox")
def get_bbox(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    if not flight.orthophoto_bbox:
        raise HTTPException(404, "Bounding box not yet computed")
    return json.loads(flight.orthophoto_bbox)


@router.get("/{flight_id}/files/{file_type}")
def serve_file(flight_id: UUID, file_type: str, db: Session = Depends(get_db)):
    if file_type not in _FILE_MAP:
        raise HTTPException(404, f"Unknown file type '{file_type}'")
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")

    rel_path, media_type = _FILE_MAP[file_type]
    path = _results_dir(str(flight_id)) / rel_path
    if not path.exists():
        raise HTTPException(404, f"File '{file_type}' not yet available")
    return FileResponse(str(path), media_type=media_type)


# ── Export ─────────────────────────────────────────────────────────────────────
@router.get("/{flight_id}/export", dependencies=[Depends(get_current_user)])
def export_flight(
    flight_id: UUID,
    format: str = Query("geotiff", regex="^(geotiff|png|csv)$"),
    db: Session = Depends(get_db),
):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")

    rdir = _results_dir(str(flight_id))

    if format == "geotiff":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            tif_map = {
                "orthophoto.tif": rdir / "odm_orthophoto" / "odm_orthophoto.tif",
                "ndvi.tif":       rdir / "ndvi.tif",
                "ndre.tif":       rdir / "ndre.tif",
                "evi.tif":        rdir / "evi.tif",
            }
            for name, path in tif_map.items():
                if path.exists():
                    zf.write(str(path), name)
        buf.seek(0)
        filename = f"results_{flight_id}.zip"
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    elif format == "png":
        png_path = rdir / "ndvi_preview.png"
        if not png_path.exists():
            raise HTTPException(404, "PNG preview not yet generated")
        return FileResponse(
            str(png_path),
            media_type="image/png",
            headers={"Content-Disposition": f'attachment; filename="ndvi_{flight_id}.png"'},
        )

    else:  # csv
        index_maps = db.query(IndexMap).filter(IndexMap.flight_id == flight_id).all()
        anomaly_zones = db.query(AnomalyZone).filter(AnomalyZone.flight_id == flight_id).all()
        anomaly_by_type: dict[str, float] = {}
        for z in anomaly_zones:
            anomaly_by_type[z.index_type] = anomaly_by_type.get(z.index_type, 0.0) + (z.area_ha or 0.0)

        date_str = flight.flown_at.strftime("%d.%m.%Y")
        sep = ";"
        lines = [sep.join([
            "Дата польоту", "Індекс", "Мінімум", "Середнє", "Максимум",
            "Аномальна площа (га)", "Поріг аномалії"
        ])]
        for im in index_maps:
            anomaly_ha = anomaly_by_type.get(im.index_type, 0.0)
            threshold = next(
                (z.threshold for z in anomaly_zones if z.index_type == im.index_type), None
            )
            lines.append(sep.join([
                date_str,
                im.index_type,
                f"{im.min_value:.4f}" if im.min_value is not None else "",
                f"{im.mean_value:.4f}" if im.mean_value is not None else "",
                f"{im.max_value:.4f}" if im.max_value is not None else "",
                f"{anomaly_ha:.4f}",
                f"{threshold:.4f}" if threshold is not None else "",
            ]))
        csv_content = "﻿" + "\n".join(lines) + "\n"
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": f'attachment; filename="flight_{flight_id}.csv"'},
        )


# ── Recommendations ──────────────────────────────────────────────────────────

def _interpret(index_type: str, mean: float, min_v: float | None, max_v: float | None) -> IndexRecommendation:
    is_proxy = False
    if index_type == "NDVI":
        # RGB proxy: all values near-zero or negative (NIR = Green approximation)
        is_proxy = max_v is None or max_v < 0.1
        # Vegetation present: strong NDVI signal in at least some pixels
        veg_present = not is_proxy and max_v is not None and max_v >= 0.3

        if is_proxy:
            category = "RGB-камера (відносний NDVI)"
            color = "blue"
            rec = (
                "Знімки зроблено звичайною RGB-камерою. NDVI розраховано приблизно "
                "(NIR ≈ Green), тому абсолютні значення від'ємні — це норма. "
                "Порівняння зон всередині поля залишається коректним. "
                "Для точного агрохімічного аналізу потрібна мультиспектральна камера."
            )
        elif veg_present and mean < 0.25:
            # High max but low mean → mixed scene (crops + roads/bare soil in frame)
            category = "Посіви + незасіяні ділянки"; color = "yellow"
            rec = (
                "Рослинність на полі присутня — зелені зони на карті відповідають активним посівам. "
                "Середнє значення знижене через наявність доріг або голого ґрунту у кадрі. "
                "Для точнішого аналізу якості посівів рекомендується проводити зйомку виключно над полем."
            )
        elif mean < 0:
            category = "Відсутня рослинність"; color = "red"
            rec = "Голий ґрунт або водна поверхня. Посіви не виявлено або поле не засіяне."
        elif mean < 0.2:
            category = "Низький"; color = "orange"
            rec = "Знижена активність рослинності. Рекомендоване підживлення азотними добривами."
        elif mean < 0.4:
            category = "Помірний"; color = "yellow"
            rec = "Задовільний стан посівів. Можливе локальне підживлення в слабших зонах."
        elif mean < 0.6:
            category = "Добрий"; color = "green"
            rec = "Хороший стан посівів. Стандартний агрономічний догляд."
        else:
            category = "Відмінний"; color = "darkgreen"
            rec = "Оптимальна активність рослинності. Додаткові заходи не потрібні."

    elif index_type == "EVI":
        veg_present_evi = max_v is not None and max_v >= 0.3
        # RGB proxy: strongly negative mean
        is_proxy = mean < -0.05 and (max_v is None or max_v < 0.3)
        # Clipping instability: RGB formula denominator → 0, values clip to ±1.0
        is_clipped = (not is_proxy) and max_v is not None and max_v >= 0.99 and mean >= 0.5

        if is_clipped or is_proxy:
            is_proxy = True
            category = "RGB-камера (EVI ненадійний)"
            color = "blue"
            rec = (
                "EVI не підходить для RGB-камер — формула чисельно нестабільна без "
                "окремого NIR-каналу. Значення зрізані до максимуму та є некоректними. "
                "Для аналізу використовуйте NDVI, який розраховано коректно. "
                "Для надійного EVI потрібна мультиспектральна камера."
            )
        elif veg_present_evi and mean < 0.2:
            category = "Змішана ділянка"; color = "yellow"
            rec = (
                "Є ділянки з активною рослинністю. Середнє значення EVI знижене "
                "через наявність доріг або незасіяного ґрунту в межах знімка."
            )
        elif mean < 0.0:
            category = "Мінімальна активність"; color = "orange"
            rec = "Дуже низька активність рослинності. Перевірте стан посівів на полі."
        elif mean < 0.2:
            category = "Помірний"; color = "yellow"
            rec = "Помірна активність листової поверхні. Стандартний моніторинг."
        elif mean < 0.4:
            category = "Добрий"; color = "green"
            rec = "Достатня листова поверхня та активна вегетація."
        else:
            category = "Відмінний"; color = "darkgreen"
            rec = "Висока листова поверхня, оптимальний стан вегетації."

    elif index_type == "NDRE":
        if mean < 0.1:
            category = "Низький хлорофіл"; color = "red"
            rec = "Низький вміст хлорофілу. Ймовірний дефіцит азоту або захворювання. Рекомендоване аркушеве живлення."
        elif mean < 0.25:
            category = "Помірний хлорофіл"; color = "orange"
            rec = "Помірний вміст хлорофілу. Розгляньте позакореневе підживлення азотом."
        else:
            category = "Достатній хлорофіл"; color = "green"
            rec = "Нормальний вміст хлорофілу. Стан відповідає нормі."
    else:
        category = "Невідомий індекс"; color = "gray"
        rec = "Недостатньо даних для інтерпретації."

    return IndexRecommendation(
        index_type=index_type, category=category, color=color,
        recommendation=rec, is_proxy=is_proxy,
    )


@router.get("/{flight_id}/recommendations", response_model=list[IndexRecommendation], dependencies=[Depends(get_current_user)])
def get_recommendations(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    index_maps = db.query(IndexMap).filter(IndexMap.flight_id == flight_id).all()
    result = []
    for im in index_maps:
        if im.mean_value is None:
            continue
        result.append(_interpret(im.index_type, im.mean_value, im.min_value, im.max_value))
    return result


# ── PDF Report ────────────────────────────────────────────────────────────────
_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _make_pdf() -> FPDF:
    pdf = FPDF()
    pdf.add_font("DejaVu", style="", fname=_FONT_PATH)
    pdf.add_font("DejaVu", style="B", fname=_FONT_BOLD_PATH)
    return pdf


@router.get("/{flight_id}/report", dependencies=[Depends(get_current_user)])
def generate_report(flight_id: UUID, db: Session = Depends(get_db)):
    flight = db.get(Flight, flight_id)
    if not flight:
        raise HTTPException(404, "Flight not found")
    if flight.status != "indices_done":
        raise HTTPException(400, "Report is only available for completed flights")

    field = db.get(Field, flight.field_id) if flight.field_id else None
    index_maps = db.query(IndexMap).filter(IndexMap.flight_id == flight_id).all()
    anomaly_zones = db.query(AnomalyZone).filter(AnomalyZone.flight_id == flight_id).all()

    pdf = _make_pdf()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 12, "Agro Monitoring — Звіт польоту", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_draw_color(76, 175, 80)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # Field + flight info
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 8, "Загальна інформація", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 11)
    pdf.cell(60, 7, "Поле:")
    pdf.cell(0, 7, field.name if field else "—", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(60, 7, "Дата польоту:")
    pdf.cell(0, 7, flight.flown_at.strftime("%d.%m.%Y %H:%M"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(60, 7, "Площа (га):")
    pdf.cell(0, 7, f"{field.area_ha:.1f}" if field and field.area_ha else "—", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(60, 7, "Статус:")
    pdf.cell(0, 7, "Завершено", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Vegetation indices table
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 8, "Вегетаційні індекси", new_x="LMARGIN", new_y="NEXT")
    pdf.set_fill_color(76, 175, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("DejaVu", "B", 10)
    col_w = [30, 35, 35, 35, 55]
    headers = ["Індекс", "Мін", "Середнє", "Макс", "Аном. площа (га)"]
    for w, h in zip(col_w, headers):
        pdf.cell(w, 8, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("DejaVu", "", 10)
    anomaly_by_type = {z.index_type: z.area_ha for z in anomaly_zones}
    fill = False
    for im in index_maps:
        pdf.set_fill_color(240, 248, 240) if fill else pdf.set_fill_color(255, 255, 255)
        anomaly_ha = anomaly_by_type.get(im.index_type, 0.0) or 0.0
        row = [
            im.index_type,
            f"{im.min_value:.4f}" if im.min_value is not None else "—",
            f"{im.mean_value:.4f}" if im.mean_value is not None else "—",
            f"{im.max_value:.4f}" if im.max_value is not None else "—",
            f"{anomaly_ha:.2f}",
        ]
        for w, val in zip(col_w, row):
            pdf.cell(w, 7, val, border=1, fill=True, align="C")
        pdf.ln()
        fill = not fill
    pdf.ln(4)

    # NDVI preview image
    rdir = _results_dir(str(flight_id))
    ndvi_png = rdir / "ndvi_preview.png"
    if ndvi_png.exists():
        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 8, "NDVI — карта поля", new_x="LMARGIN", new_y="NEXT")
        page_w = pdf.w - pdf.l_margin - pdf.r_margin
        pdf.image(str(ndvi_png), x=pdf.l_margin, w=page_w)
        pdf.ln(3)

    # Recommendations
    recs = []
    for im in index_maps:
        if im.mean_value is not None:
            recs.append(_interpret(im.index_type, im.mean_value, im.min_value, im.max_value))

    if recs:
        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 8, "Рекомендації", new_x="LMARGIN", new_y="NEXT")
        _COLOR_MAP = {
            "red": (220, 53, 69), "orange": (255, 152, 0), "yellow": (255, 193, 7),
            "green": (76, 175, 80), "darkgreen": (27, 94, 32), "blue": (33, 150, 243), "gray": (158, 158, 158),
        }
        for rec in recs:
            r, g, b = _COLOR_MAP.get(rec.color, (100, 100, 100))
            pdf.set_fill_color(r, g, b)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("DejaVu", "B", 10)
            pdf.cell(0, 7, f"  {rec.index_type}: {rec.category}", fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("DejaVu", "", 10)
            pdf.multi_cell(0, 6, rec.recommendation)
            pdf.ln(2)

    # Notes
    if flight.notes:
        pdf.set_font("DejaVu", "B", 12)
        pdf.cell(0, 8, "Нотатки", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("DejaVu", "", 11)
        pdf.multi_cell(0, 6, flight.notes)
        pdf.ln(2)

    # Footer
    pdf.set_y(-20)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, f"Agro Monitoring System  |  {flight.flown_at.strftime('%d.%m.%Y')}", align="C")

    buf = io.BytesIO(pdf.output())
    filename = f"report_{flight_id}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Anomalies GeoJSON ─────────────────────────────────────────────────────────
@router.get("/{flight_id}/anomalies", dependencies=[Depends(get_current_user)])
def get_anomalies(flight_id: UUID, db: Session = Depends(get_db)):
    zones = db.query(AnomalyZone).filter(AnomalyZone.flight_id == flight_id).all()
    features = [
        {
            "type": "Feature",
            "geometry": mapping(to_shape(z.zone_geom)),
            "properties": {
                "id": str(z.id),
                "index_type": z.index_type,
                "area_ha": z.area_ha,
                "threshold": z.threshold,
            },
        }
        for z in zones
        if z.zone_geom is not None
    ]
    return {"type": "FeatureCollection", "features": features}
