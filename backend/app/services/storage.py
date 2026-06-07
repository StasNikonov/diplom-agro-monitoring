from pathlib import Path


def ensure_flight_dirs(flight_id: str, data_dir: str) -> tuple[Path, Path]:
    raw = Path(data_dir) / "flights" / flight_id / "raw"
    results = Path(data_dir) / "flights" / flight_id / "results"
    raw.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    return raw, results


def flight_raw_path(flight_id: str, data_dir: str) -> Path:
    return Path(data_dir) / "flights" / flight_id / "raw"


def flight_results_path(flight_id: str, data_dir: str) -> Path:
    return Path(data_dir) / "flights" / flight_id / "results"
