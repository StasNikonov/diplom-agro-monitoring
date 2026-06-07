"""Vegetation indices pipeline: NDVI, NDRE, EVI + colored PNG previews + orthophoto bbox."""
import json
import logging
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.warp import transform_bounds

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_EPS = 1e-10


def _stats(arr: np.ndarray, veg_threshold: float | None = None) -> tuple[float | None, float | None, float | None]:
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return None, None, None
    # mean is computed over "vegetated" pixels only to exclude roads/bare soil
    mean_pixels = valid[valid > veg_threshold] if veg_threshold is not None else valid
    mean_val = float(mean_pixels.mean()) if mean_pixels.size > 0 else float(valid.mean())
    return float(valid.min()), float(valid.max()), mean_val


def _write_tif(path: Path, data: np.ndarray, meta: dict) -> None:
    m = {**meta, "count": 1, "dtype": "float32", "nodata": float("nan")}
    with rasterio.open(path, "w", **m) as dst:
        dst.write(data.astype(np.float32), 1)


_MAX_PREVIEW_PX = 3000  # stay well under WebGL max texture size (4096)


def _write_preview(path: Path, arr: np.ndarray, nodata_mask: np.ndarray) -> None:
    """Red-to-green RGBA PNG preview for map overlay, capped at _MAX_PREVIEW_PX."""
    valid = arr[np.isfinite(arr) & ~nodata_mask]
    if valid.size > 0:
        lo, hi = np.percentile(valid, [2, 98])
        norm = np.clip((arr.astype(np.float32) - lo) / (hi - lo + _EPS), 0.0, 1.0)
    else:
        norm = np.clip((arr.astype(np.float32) + 1.0) / 2.0, 0.0, 1.0)
    r = ((1.0 - norm) * 255).astype(np.uint8)
    g = (norm * 255).astype(np.uint8)
    b = np.zeros_like(r)
    a = np.where(nodata_mask | ~np.isfinite(arr), 0, 255).astype(np.uint8)
    img = Image.fromarray(np.stack([r, g, b, a], axis=-1), "RGBA")
    h, w = arr.shape
    if max(h, w) > _MAX_PREVIEW_PX:
        scale = _MAX_PREVIEW_PX / max(h, w)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img.save(str(path), format="PNG")


def run_indices_pipeline(flight_id: str) -> None:
    logger.info("Indices pipeline started for flight %s", flight_id)

    from app.config import settings
    from app.database import SessionLocal
    from app.models import Flight, IndexMap

    results_dir = Path(settings.data_dir) / "flights" / flight_id / "results"
    ortho_path = results_dir / "odm_orthophoto" / "odm_orthophoto.tif"

    if not ortho_path.exists():
        logger.error("Orthophoto not found at %s", ortho_path)
        return

    db = SessionLocal()
    try:
        # Remove stale index maps so re-runs don't create duplicates
        db.query(IndexMap).filter(IndexMap.flight_id == flight_id).delete()
        db.flush()

        with rasterio.open(ortho_path) as src:
            n_bands = src.count
            meta = src.meta.copy()
            nodata = src.nodata

            if n_bands >= 5:
                # Multispectral: Blue/Green/Red/RedEdge/NIR
                blue = src.read(1).astype(np.float32)
                red = src.read(3).astype(np.float32)
                red_edge = src.read(4).astype(np.float32)
                nir = src.read(5).astype(np.float32)
                multispectral = True
            elif n_bands in (3, 4):
                # Standard RGB or RGBA orthophoto — compute visible-band proxies
                # Band order for ODM RGB output: R=1, G=2, B=3 (band 4 = Alpha if present)
                red = src.read(1).astype(np.float32)
                green = src.read(2).astype(np.float32)
                blue = src.read(3).astype(np.float32)
                # Proxy NIR ≈ Green (common approximation for RGB-only sensors)
                nir = green.copy()
                red_edge = green.copy()
                multispectral = False
                logger.info("RGB%s orthophoto — using visible-band proxy indices", "A" if n_bands == 4 else "")
            else:
                logger.error("Orthophoto has %d bands — unsupported", n_bands)
                return

            # Build nodata mask from alpha band or nodata value
            nodata_mask = np.zeros(red.shape, dtype=bool)
            if n_bands == 4:
                # Alpha band = 0 means transparent (no data)
                alpha = src.read(4)
                nodata_mask |= alpha == 0
            elif nodata is not None:
                for b in range(1, min(n_bands, 3) + 1):
                    nodata_mask |= src.read(b) == nodata

            # Store orthophoto bbox in WGS84
            west, south, east, north = transform_bounds(
                src.crs, "EPSG:4326",
                src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top,
            )

        # ── Orthophoto PNG preview ────────────────────────────────────────────
        with rasterio.open(ortho_path) as src:
            r8_raw = src.read(1)
            g8_raw = src.read(2)
            b8_raw = src.read(3)

        def _to_uint8(band: np.ndarray) -> np.ndarray:
            b = band.astype(np.float32)
            valid = b[b > 0]
            if valid.size == 0:
                return np.zeros_like(band, dtype=np.uint8)
            lo, hi = np.percentile(valid, [2, 98])
            return np.clip((b - lo) / (hi - lo + _EPS) * 255, 0, 255).astype(np.uint8)

        alpha8 = np.where(nodata_mask, 0, 255).astype(np.uint8)
        ortho_img = Image.fromarray(
            np.stack([_to_uint8(r8_raw), _to_uint8(g8_raw), _to_uint8(b8_raw), alpha8], axis=-1), "RGBA"
        )
        oh, ow = r8_raw.shape
        if max(oh, ow) > _MAX_PREVIEW_PX:
            scale = _MAX_PREVIEW_PX / max(oh, ow)
            ortho_img = ortho_img.resize((int(ow * scale), int(oh * scale)), Image.LANCZOS)
        ortho_img.save(str(results_dir / "orthophoto_preview.png"), format="PNG")
        logger.info("Orthophoto PNG preview saved")

        # ── NDVI ──────────────────────────────────────────────────────────────
        ndvi = np.clip((nir - red) / (nir + red + _EPS), -1.0, 1.0).astype(np.float32)
        ndvi[nodata_mask] = np.nan
        _write_tif(results_dir / "ndvi.tif", ndvi, meta)
        _write_preview(results_dir / "ndvi_preview.png", ndvi, nodata_mask)
        # mean excludes roads/bare soil (pixels below -0.2 threshold)
        mn, mx, me = _stats(ndvi, veg_threshold=-0.2)
        logger.info("NDVI: min=%.4f max=%.4f mean=%.4f", mn or 0, mx or 0, me or 0)
        db.add(IndexMap(flight_id=flight_id, index_type="NDVI",
                        file_path=str(results_dir / "ndvi.tif"),
                        min_value=mn, max_value=mx, mean_value=me))

        if multispectral:
            # ── EVI (multispectral only — formula is numerically unstable on RGB proxy) ──
            evi = np.clip(
                2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1 + _EPS),
                -1.0, 1.0,
            ).astype(np.float32)
            evi[nodata_mask] = np.nan
            _write_tif(results_dir / "evi.tif", evi, meta)
            _write_preview(results_dir / "evi_preview.png", evi, nodata_mask)
            mn, mx, me = _stats(evi, veg_threshold=-0.2)
            logger.info("EVI: min=%.4f max=%.4f mean=%.4f", mn or 0, mx or 0, me or 0)
            db.add(IndexMap(flight_id=flight_id, index_type="EVI",
                            file_path=str(results_dir / "evi.tif"),
                            min_value=mn, max_value=mx, mean_value=me))

        if n_bands >= 5:
            # ── NDRE (multispectral only) ──────────────────────────────────────
            ndre = np.clip((nir - red_edge) / (nir + red_edge + _EPS), -1.0, 1.0).astype(np.float32)
            ndre[nodata_mask] = np.nan
            _write_tif(results_dir / "ndre.tif", ndre, meta)
            _write_preview(results_dir / "ndre_preview.png", ndre, nodata_mask)
            mn, mx, me = _stats(ndre)
            logger.info("NDRE: min=%.4f max=%.4f mean=%.4f", mn or 0, mx or 0, me or 0)
            db.add(IndexMap(flight_id=flight_id, index_type="NDRE",
                            file_path=str(results_dir / "ndre.tif"),
                            min_value=mn, max_value=mx, mean_value=me))

        # ── DSM preview ───────────────────────────────────────────────────────
        dsm_path = results_dir / "odm_dem" / "dsm.tif"
        if dsm_path.exists():
            try:
                with rasterio.open(dsm_path) as dsm_src:
                    dsm_data = dsm_src.read(1).astype(np.float32)
                    dsm_nodata = dsm_src.nodata
                dsm_mask = ~np.isfinite(dsm_data)
                if dsm_nodata is not None:
                    dsm_mask |= dsm_data == dsm_nodata
                valid_dsm = dsm_data[~dsm_mask]
                if valid_dsm.size > 0:
                    lo, hi = np.percentile(valid_dsm, [2, 98])
                    n = np.clip((dsm_data - lo) / (hi - lo + _EPS), 0.0, 1.0)
                else:
                    n = np.zeros_like(dsm_data)
                # Terrain colormap: blue→cyan→green→yellow→red
                r_d = np.zeros_like(n, dtype=np.uint8)
                g_d = np.zeros_like(n, dtype=np.uint8)
                b_d = np.zeros_like(n, dtype=np.uint8)
                m0 = n < 0.25;  t0 = n[m0] / 0.25
                r_d[m0] = 0;               g_d[m0] = (t0 * 128).astype(np.uint8);          b_d[m0] = (128 + t0 * 127).astype(np.uint8)
                m1 = (n >= 0.25) & (n < 0.5);  t1 = (n[m1] - 0.25) / 0.25
                r_d[m1] = 0;               g_d[m1] = (128 + t1 * 127).astype(np.uint8);    b_d[m1] = (255 * (1 - t1)).astype(np.uint8)
                m2 = (n >= 0.5) & (n < 0.75);  t2 = (n[m2] - 0.5) / 0.25
                r_d[m2] = (t2 * 255).astype(np.uint8);  g_d[m2] = 255;                     b_d[m2] = 0
                m3 = n >= 0.75;            t3 = (n[m3] - 0.75) / 0.25
                r_d[m3] = 255;             g_d[m3] = (255 * (1 - t3)).astype(np.uint8);    b_d[m3] = 0
                a_d = np.where(dsm_mask, 0, 200).astype(np.uint8)
                dsm_img = Image.fromarray(np.stack([r_d, g_d, b_d, a_d], axis=-1), "RGBA")
                dh, dw = dsm_data.shape
                if max(dh, dw) > _MAX_PREVIEW_PX:
                    sc = _MAX_PREVIEW_PX / max(dh, dw)
                    dsm_img = dsm_img.resize((int(dw * sc), int(dh * sc)), Image.LANCZOS)
                dsm_img.save(str(results_dir / "dsm_preview.png"), format="PNG")
                logger.info("DSM preview saved")
            except Exception as exc:
                logger.warning("DSM preview failed: %s", exc)

        flight = db.get(Flight, flight_id)
        if flight:
            flight.status = "indices_done"
            flight.orthophoto_bbox = json.dumps([west, south, east, north])

        db.commit()
        logger.info("Indices + bbox saved for flight %s", flight_id)

    except Exception as exc:
        logger.error("Indices pipeline failed for %s: %s", flight_id, exc, exc_info=True)
        db.rollback()
        return
    finally:
        db.close()

    from tasks.segmentation_task import run_segmentation
    run_segmentation(flight_id)
