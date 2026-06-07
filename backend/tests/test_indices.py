"""Unit tests for vegetation index math — no DB, no filesystem."""
import numpy as np
import pytest

_EPS = 1e-10


def _ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return (nir - red) / (nir + red + _EPS)


def _ndre(red_edge: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return (nir - red_edge) / (nir + red_edge + _EPS)


def _evi(blue: np.ndarray, red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    return 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1.0 + _EPS)


def test_ndvi_healthy_vegetation():
    red = np.array([0.1], dtype=np.float32)
    nir = np.array([0.9], dtype=np.float32)
    result = _ndvi(red, nir)
    assert result[0] == pytest.approx(0.8, abs=1e-3)


def test_ndvi_bare_soil():
    red = np.array([0.5], dtype=np.float32)
    nir = np.array([0.5], dtype=np.float32)
    result = _ndvi(red, nir)
    assert abs(result[0]) < 0.001


def test_ndvi_no_division_by_zero():
    red = np.zeros(5, dtype=np.float32)
    nir = np.zeros(5, dtype=np.float32)
    result = _ndvi(red, nir)
    assert np.all(np.isfinite(result))


def test_ndvi_range():
    rng = np.random.default_rng(42)
    red = rng.uniform(0, 1, 1000).astype(np.float32)
    nir = rng.uniform(0, 1, 1000).astype(np.float32)
    result = _ndvi(red, nir)
    assert np.all(result >= -1.0 - 1e-6)
    assert np.all(result <= 1.0 + 1e-6)


def test_ndre_range():
    rng = np.random.default_rng(0)
    red_edge = rng.uniform(0, 1, 500).astype(np.float32)
    nir = rng.uniform(0, 1, 500).astype(np.float32)
    result = _ndre(red_edge, nir)
    assert np.all(result >= -1.0 - 1e-6)
    assert np.all(result <= 1.0 + 1e-6)


def test_evi_typical_value():
    blue = np.array([0.05], dtype=np.float32)
    red = np.array([0.1], dtype=np.float32)
    nir = np.array([0.5], dtype=np.float32)
    result = _evi(blue, red, nir)
    # EVI for healthy veg is roughly 0.3–0.6
    assert 0.2 < result[0] < 0.9


def test_evi_no_nan():
    blue = np.zeros(10, dtype=np.float32)
    red = np.zeros(10, dtype=np.float32)
    nir = np.zeros(10, dtype=np.float32)
    result = _evi(blue, red, nir)
    assert np.all(np.isfinite(result))
