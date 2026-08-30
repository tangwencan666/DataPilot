import multiprocessing as mp
import queue
import time
from pathlib import Path

import pandas as pd

from app.analysis.errors import AnalysisError, AnalysisTimeoutError
from app.analysis.executor import PandasAnalysisExecutor
from app.analysis.schemas import AnalysisPlan, AnalysisResult
from app.config import Settings
from app.parsers import load_dataframe


def analysis_worker(payload: dict, output_queue) -> None:
    try:
        settings = Settings(**payload["settings"])
        path = Path(payload["path"])
        if payload["file_type"] == "csv" and payload["sampled"]:
            frame = pd.read_csv(path, nrows=settings.analysis_sample_rows)
        else:
            frame, _ = load_dataframe(path.read_bytes(), payload["file_type"])
            if payload["sampled"]:
                frame = frame.head(settings.analysis_sample_rows)
        result = PandasAnalysisExecutor(settings).execute(frame, AnalysisPlan.model_validate(payload["plan"]), payload["sampled"])
        result.metadata["source_rows"] = payload["source_rows"]
        output_queue.put({"ok": True, "result": result.model_dump(mode="json")})
    except AnalysisError as exc:
        output_queue.put({"ok": False, "code": exc.code, "message": exc.detail})
    except Exception:
        output_queue.put({"ok": False, "code": "ANALYSIS_EXECUTION_FAILED", "message": "Controlled analysis execution failed."})


def _test_sleep_worker(payload: dict, output_queue) -> None:
    time.sleep(payload.get("sleep", 5))


class AnalysisProcessRunner:
    def __init__(self, settings: Settings, target=analysis_worker) -> None:
        self.settings = settings
        self.target = target

    def run(self, payload: dict) -> AnalysisResult:
        context = mp.get_context("spawn")
        output = context.Queue(maxsize=1)
        process = context.Process(target=self.target, args=(payload, output))
        process.start()
        process.join(self.settings.analysis_timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(2)
            if process.is_alive():
                process.kill()
                process.join()
            raise AnalysisTimeoutError("Analysis exceeded the configured timeout and its worker was terminated.")
        try:
            message = output.get(timeout=1)
        except queue.Empty:
            raise AnalysisError("Analysis worker exited without a result.")
        finally:
            output.close()
            output.join_thread()
        if not message["ok"]:
            error = AnalysisError(message["message"])
            error.code = message["code"]
            raise error
        return AnalysisResult.model_validate(message["result"])
