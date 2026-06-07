"""ODM pipeline task: submit images to NodeODM, poll for completion, download results."""
import json
import logging
import time
import zipfile
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_STATUS_QUEUED = 10
_STATUS_RUNNING = 20
_STATUS_FAILED = 30
_STATUS_COMPLETED = 40
_STATUS_CANCELED = 50

_POLL_INTERVAL = 30
_MAX_WAIT_SECONDS = 4 * 60 * 60


def run_odm_pipeline(flight_id: str) -> None:
    logger.info("ODM pipeline started for flight %s", flight_id)

    from app.config import settings
    from app.database import SessionLocal
    from app.models import Flight

    db = SessionLocal()
    client = httpx.Client(timeout=None)

    try:
        # ── Step 1: preparation ───────────────────────────────────────────────
        flight = db.get(Flight, flight_id)
        if not flight:
            logger.error("Flight %s not found in DB", flight_id)
            return

        raw_dir = Path(settings.data_dir) / "flights" / flight_id / "raw"
        image_files = sorted(
            p for p in raw_dir.iterdir()
            if p.suffix.lower() in {".jpg", ".jpeg", ".tif", ".tiff"}
        ) if raw_dir.exists() else []

        if not image_files:
            logger.error("No images in %s for flight %s", raw_dir, flight_id)
            flight.status = "odm_failed"
            db.commit()
            raise RuntimeError(f"No images found in {raw_dir}")

        logger.info("Found %d images for flight %s", len(image_files), flight_id)

        # ── Step 2: submit to NodeODM ─────────────────────────────────────────
        options = [
            {"name": "orthophoto-resolution", "value": 5},
            {"name": "max-concurrency", "value": 2},
            {"name": "feature-quality", "value": "medium"},
            {"name": "pc-quality", "value": "low"},
            {"name": "skip-3dmodel", "value": True},
            {"name": "fast-orthophoto", "value": True},
        ]

        file_handles = []
        multipart_files = []
        for img in image_files:
            fh = open(img, "rb")
            file_handles.append(fh)
            multipart_files.append(("images", (img.name, fh)))

        try:
            resp = client.post(
                f"{settings.nodeodm_url}/task/new",
                files=multipart_files,
                data={"options": json.dumps(options)},
            )
            resp.raise_for_status()
            odm_task_uuid = resp.json()["uuid"]
            logger.info("NodeODM task created: %s", odm_task_uuid)
        except Exception as exc:
            logger.error("Failed to submit to NodeODM: %s", exc)
            flight.status = "odm_failed"
            db.commit()
            return
        finally:
            for fh in file_handles:
                fh.close()

        flight.odm_task_uuid = odm_task_uuid
        flight.status = "odm_processing"
        db.commit()

        # ── Step 3: polling ───────────────────────────────────────────────────
        elapsed = 0
        completed = False

        while elapsed < _MAX_WAIT_SECONDS:
            time.sleep(_POLL_INTERVAL)
            elapsed += _POLL_INTERVAL

            try:
                info_resp = client.get(
                    f"{settings.nodeodm_url}/task/{odm_task_uuid}/info",
                    timeout=30,
                )
                info_resp.raise_for_status()
                info = info_resp.json()
                code = info["status"]["code"]
                progress = info.get("progress", 0.0)
                proc_time = info.get("processingTime", 0)

                logger.info(
                    "ODM task %s: code=%d progress=%.1f%% elapsed=%ds proc_time=%ds",
                    odm_task_uuid, code, progress, elapsed, proc_time,
                )

                if code == _STATUS_COMPLETED:
                    completed = True
                    break
                elif code in (_STATUS_FAILED, _STATUS_CANCELED):
                    logger.error("ODM task %s terminated with code %d", odm_task_uuid, code)
                    db.get(Flight, flight_id).status = "odm_failed"
                    db.commit()
                    return

            except Exception as exc:
                logger.warning("Poll error for ODM task %s: %s", odm_task_uuid, exc)

        if not completed:
            logger.error("ODM task %s timed out after %ds", odm_task_uuid, _MAX_WAIT_SECONDS)
            db.get(Flight, flight_id).status = "odm_failed"
            db.commit()
            return

        # ── Step 4: download and extract results ──────────────────────────────
        results_dir = Path(settings.data_dir) / "flights" / flight_id / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        zip_path = results_dir / "all.zip"

        try:
            logger.info("Downloading results for ODM task %s", odm_task_uuid)
            with client.stream(
                "GET",
                f"{settings.nodeodm_url}/task/{odm_task_uuid}/download/all.zip",
            ) as dl:
                dl.raise_for_status()
                with open(zip_path, "wb") as f:
                    for chunk in dl.iter_bytes(chunk_size=65536):
                        f.write(chunk)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(results_dir)
            zip_path.unlink()
            logger.info("Results extracted to %s", results_dir)

            ortho = results_dir / "odm_orthophoto" / "odm_orthophoto.tif"
            dsm = results_dir / "odm_dem" / "dsm.tif"

            if not ortho.exists():
                raise FileNotFoundError(f"Expected orthophoto at {ortho}")
            if not dsm.exists():
                logger.warning("DSM not found at %s — continuing without it", dsm)

            db.get(Flight, flight_id).status = "odm_done"
            db.commit()
            logger.info("ODM done for flight %s", flight_id)

        except Exception as exc:
            logger.error("Error downloading ODM results for %s: %s", flight_id, exc, exc_info=True)
            db.get(Flight, flight_id).status = "odm_failed"
            db.commit()
            return

    finally:
        db.close()
        client.close()

    # ── Chain: run indices in same RQ job ─────────────────────────────────────
    from tasks.indices_task import run_indices_pipeline
    run_indices_pipeline(flight_id)
