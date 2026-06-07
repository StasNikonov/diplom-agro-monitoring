"""Segmentation task: vectorise low-NDVI zones and store anomaly polygons."""
import logging
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod, Transformer
from rasterio.features import shapes
from shapely.geometry import MultiPolygon, Polygon, shape as shapely_shape
from shapely.ops import transform as shapely_transform, unary_union

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_MIN_AREA_M2 = 100.0  # 0.01 ha
_STD_MULTIPLIER = 1.5  # pixels below (mean - 1.5*std) are anomalous


def run_segmentation(flight_id: str) -> None:
    logger.info("Segmentation started for flight %s", flight_id)

    from app.config import settings
    from app.database import SessionLocal
    from app.models import AnomalyZone
    from geoalchemy2.shape import from_shape

    results_dir = Path(settings.data_dir) / "flights" / flight_id / "results"
    ndvi_path = results_dir / "ndvi.tif"

    if not ndvi_path.exists():
        logger.error("NDVI raster not found at %s", ndvi_path)
        return

    db = SessionLocal()
    try:
        # ── Step 0: remove stale anomaly zones ───────────────────────────────
        db.query(AnomalyZone).filter(AnomalyZone.flight_id == flight_id).delete()
        db.flush()

        # ── Step 1: load NDVI raster ──────────────────────────────────────────
        with rasterio.open(ndvi_path) as src:
            ndvi = src.read(1)
            transform = src.transform
            src_crs = src.crs

        # ── Step 2: compute relative threshold (mean - 1.5*std) ──────────────
        valid = ndvi[np.isfinite(ndvi)]
        mean_val = float(np.mean(valid))
        std_val = float(np.std(valid))
        threshold = mean_val - _STD_MULTIPLIER * std_val
        logger.info(
            "NDVI stats for flight %s: mean=%.4f std=%.4f threshold=%.4f",
            flight_id, mean_val, std_val, threshold,
        )

        low_mask = (ndvi < threshold) & np.isfinite(ndvi)
        mask_uint8 = low_mask.astype(np.uint8)

        raw_polygons = []
        for geom_dict, value in shapes(mask_uint8, mask=mask_uint8, transform=transform):
            if value == 1:
                raw_polygons.append(shapely_shape(geom_dict))

        if not raw_polygons:
            logger.info("No low-NDVI zones found for flight %s", flight_id)
            return

        logger.info("Vectorised %d raw polygons for flight %s", len(raw_polygons), flight_id)

        # ── Step 3: reproject to WGS84 ───────────────────────────────────────
        transformer = Transformer.from_crs(src_crs, "EPSG:4326", always_xy=True)

        def _reproject(geom):
            return shapely_transform(transformer.transform, geom)

        wgs84_polygons = [_reproject(p) for p in raw_polygons]

        # ── Step 4: filter by area (geodesic) ────────────────────────────────
        geod = Geod(ellps="WGS84")
        filtered = []
        for poly in wgs84_polygons:
            area_m2 = abs(geod.geometry_area_perimeter(poly)[0])
            if area_m2 >= _MIN_AREA_M2:
                filtered.append(poly)

        if not filtered:
            logger.info("All polygons below min area threshold for flight %s", flight_id)
            return

        logger.info("%d polygons remain after area filter for flight %s", len(filtered), flight_id)

        # ── Step 5: union into MultiPolygon ──────────────────────────────────
        merged = unary_union(filtered)
        if merged.is_empty:
            return

        if isinstance(merged, Polygon):
            multi = MultiPolygon([merged])
        elif isinstance(merged, MultiPolygon):
            multi = merged
        else:
            # GeometryCollection — keep only polygons
            polys = [g for g in merged.geoms if isinstance(g, Polygon)]
            if not polys:
                return
            multi = MultiPolygon(polys)

        total_area_m2 = abs(geod.geometry_area_perimeter(multi)[0])
        total_area_ha = total_area_m2 / 10_000
        logger.info("Total anomaly area: %.2f ha for flight %s", total_area_ha, flight_id)

        # ── Step 6: save to DB ────────────────────────────────────────────────
        zone = AnomalyZone(
            flight_id=flight_id,
            index_type="NDVI",
            zone_geom=from_shape(multi, srid=4326),
            threshold=round(threshold, 4),
            area_ha=total_area_ha,
        )
        db.add(zone)
        db.commit()
        logger.info("Anomaly zone saved for flight %s (area=%.2f ha)", flight_id, total_area_ha)

    except Exception as exc:
        logger.error("Segmentation failed for flight %s: %s", flight_id, exc, exc_info=True)
        db.rollback()
    finally:
        db.close()
