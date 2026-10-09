from concurrent.futures import ThreadPoolExecutor
import logging
from threading import Lock


class TripJobManager:
    def __init__(self, max_workers=4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="roam-trip")
        self._lock = Lock()
        self._jobs = {}

    def start(self, job_id, worker, trip_details, total_steps):
        with self._lock:
            self._jobs[job_id] = {
                "trip_details": trip_details,
                "label": "Connecting to travel research...",
                "completed": 0,
                "total": total_steps,
                "steps": [],
                "done": False,
                "result": None,
                "error": None,
            }
            stale_jobs = [key for key, job in self._jobs.items() if job["done"] and key != job_id]
            for key in stale_jobs[:-50]:
                del self._jobs[key]
        self._executor.submit(self._run, job_id, worker)

    def _run(self, job_id, worker):
        try:
            result = worker(
                lambda label, completed, total: self._update(
                    job_id, label=label, completed=completed, total=total
                )
            )
        except Exception as error:
            logging.exception("Travel planning job failed")
            self._update(job_id, done=True, error=type(error).__name__)
        else:
            self._update(job_id, done=True, result=result)

    def _update(self, job_id, **changes):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            completed = changes.get("completed", 0)
            if completed > job["completed"] and changes.get("label"):
                job["steps"].append(changes["label"])
            job.update(changes)

    def snapshot(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            snapshot = dict(job)
            snapshot["steps"] = list(job["steps"])
            return snapshot

    def discard(self, job_id):
        with self._lock:
            self._jobs.pop(job_id, None)
