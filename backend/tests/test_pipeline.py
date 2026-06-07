"""Integration test for the indices pipeline using a synthetic 5-band GeoTIFF."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

try:
    import rasterio
    from rasterio.transform import from_bounds
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

pytestmark = pytest.mark.skipif(not RASTERIO_AVAILABLE, reason="rasterio not installed")


def _create_synthetic_orthophoto(path: Path) -> None:
    """Write a 5-band (Blue/Green/Red/RedEdge/NIR) GeoTIFF at 1°×1° near Kyiv."""
    width, height = 64, 64
    transform = from_bounds(30.0, 50.0, 31.0, 51.0, width, height)
    rng = np.random.default_rng(123)
    bands = rng.uniform(0.05, 0.9, (5, height, width)).astype(np.float32)
    # NIR (band 5) brighter than red (band 3) for positive NDVI
    bands[4] = np.clip(bands[2] + 0.3, 0, 1)

    with rasterio.open(
        path, "w",
        driver="GTiff",
        height=height,
        width=width,
        count=5,
        dtype="float32",
        crs="EPSG:32636",
        transform=transform,
    ) as dst:
        for i, band in enumerate(bands, 1):
            dst.write(band, i)


def test_indices_pipeline_produces_outputs(tmp_path, monkeypatch):
    """Run run_indices_pipeline end-to-end with a synthetic orthophoto."""
    import uuid

    flight_id = str(uuid.uuid4())
    data_dir = tmp_path / "data"
    results_dir = data_dir / "flights" / flight_id / "results" / "odm_orthophoto"
    results_dir.mkdir(parents=True)
    ortho_path = results_dir / "odm_orthophoto.tif"
    _create_synthetic_orthophoto(ortho_path)

    # Mock DB session
    saved_flight = {}
    saved_index_maps = []

    class FakeFlight:
        id = flight_id
        status = "odm_done"
        orthophoto_bbox = None

        def __setattr__(self, name, value):
            super().__setattr__(name, value)
            saved_flight[name] = value

    class FakeIndexMap:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeDB:
        def __init__(self):
            self._flight = FakeFlight()

        def get(self, model, id_):
            return self._flight

        def add(self, obj):
            saved_index_maps.append(obj)

        def commit(self):
            pass

        def refresh(self, obj):
            pass

        def close(self):
            pass

    fake_db = FakeDB()

    monkeypatch.setenv("DATA_DIR", str(data_dir))

    # Patch imports used inside run_indices_pipeline
    import sys
    import types

    # Patch app.config.settings
    fake_settings = types.SimpleNamespace(data_dir=str(data_dir))
    fake_config = types.ModuleType("app.config")
    fake_config.settings = fake_settings
    monkeypatch.setitem(sys.modules, "app.config", fake_config)

    fake_db_module = types.ModuleType("app.database")
    fake_db_module.SessionLocal = lambda: fake_db
    monkeypatch.setitem(sys.modules, "app.database", fake_db_module)

    fake_models = types.ModuleType("app.models")
    fake_models.Flight = FakeFlight
    fake_models.IndexMap = FakeIndexMap
    monkeypatch.setitem(sys.modules, "app.models", fake_models)

    # Also need segmentation_task stub
    fake_seg = types.ModuleType("tasks.segmentation_task")
    fake_seg.run_segmentation = lambda *a, **kw: None
    monkeypatch.setitem(sys.modules, "tasks.segmentation_task", fake_seg)

    import importlib
    indices_mod = importlib.import_module("tasks.indices_task")
    importlib.reload(indices_mod)

    indices_mod.run_indices_pipeline(flight_id)

    # Verify output files
    flight_results = data_dir / "flights" / flight_id / "results"
    assert (flight_results / "ndvi.tif").exists(), "ndvi.tif not created"
    assert (flight_results / "ndvi_preview.png").exists(), "ndvi_preview.png not created"
    assert (flight_results / "ndre.tif").exists(), "ndre.tif not created"
    assert (flight_results / "evi.tif").exists(), "evi.tif not created"

    # Verify bbox was stored
    assert saved_flight.get("orthophoto_bbox") is not None
    bbox = json.loads(saved_flight["orthophoto_bbox"])
    assert len(bbox) == 4
    west, south, east, north = bbox
    assert -180 <= west < east <= 180
    assert -90 <= south < north <= 90

    # Verify index maps were saved
    assert len(saved_index_maps) >= 3
    index_types = {im.index_type for im in saved_index_maps}
    assert "NDVI" in index_types
    assert "NDRE" in index_types
    assert "EVI" in index_types
