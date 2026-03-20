import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:
    firebase_admin = None
    credentials = None
    firestore = None


class BaseStore:
    mode = "base"

    def create_share(self, share_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_share(self, share_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def update_share(self, share_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def create_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def list_projects(self, owner_uid: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def delete_project(self, owner_uid: str, project_id: str) -> bool:
        raise NotImplementedError

    def create_published(self, published_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_published(self, published_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def create_portfolio(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def list_portfolios(self, owner_uid: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def update_portfolio(self, portfolio_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def delete_portfolio(self, owner_uid: str, portfolio_id: str) -> bool:
        raise NotImplementedError

    def create_converter_upload(self, upload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_converter_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def list_converter_uploads(self, owner_uid: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def create_converter_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_converter_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def list_converter_jobs(self, owner_uid: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def list_all_converter_jobs(self, limit: int = 200) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def delete_converter_upload(self, upload_id: str) -> bool:
        raise NotImplementedError

    def delete_converter_job(self, job_id: str) -> bool:
        raise NotImplementedError


class JsonFileStore(BaseStore):
    mode = "json"

    def __init__(self, data_path: Path):
        is_vercel = os.getenv("VERCEL", "").strip().lower() == "true"
        if is_vercel:
            self.data_path = Path("/tmp") / "storage.json"
        else:
            self.data_path = data_path
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._bootstrap()

    def _bootstrap(self) -> None:
        if self.data_path.exists():
            return
        self._write(
            {
                "shares": {},
                "projects": {},
                "published": {},
                "portfolios": {},
                "converter_uploads": {},
                "converter_jobs": {},
            }
        )

    def _read(self) -> Dict[str, Any]:
        with self.data_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        changed = False
        for key, default in {
            "shares": {},
            "projects": {},
            "published": {},
            "portfolios": {},
            "converter_uploads": {},
            "converter_jobs": {},
        }.items():
            if key not in data:
                data[key] = default
                changed = True
        if changed:
            self._write(data)
        return data

    def _write(self, payload: Dict[str, Any]) -> None:
        temp_path = self.data_path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2)
        temp_path.replace(self.data_path)

    def create_share(self, share_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            data["shares"][share_id] = item
            self._write(data)
            return dict(data["shares"][share_id])

    def get_share(self, share_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            item = data["shares"].get(share_id)
            return dict(item) if item else None

    def update_share(self, share_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            item = data["shares"].get(share_id)
            if not item:
                return None
            item.update(updates)
            data["shares"][share_id] = item
            self._write(data)
            return dict(item)

    def create_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        owner_uid = project.get("owner_uid", "")
        with self._lock:
            data = self._read()
            projects = data["projects"].get(owner_uid, [])
            projects = [p for p in projects if p.get("id") != project.get("id")]
            projects.insert(0, project)
            data["projects"][owner_uid] = projects[:100]
            self._write(data)
            return dict(project)

    def list_projects(self, owner_uid: str) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            return list(data["projects"].get(owner_uid, []))

    def delete_project(self, owner_uid: str, project_id: str) -> bool:
        with self._lock:
            data = self._read()
            projects = data["projects"].get(owner_uid, [])
            filtered = [project for project in projects if project.get("id") != project_id]
            deleted = len(filtered) != len(projects)
            data["projects"][owner_uid] = filtered
            self._write(data)
            return deleted

    def create_published(self, published_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            data["published"][published_id] = item
            self._write(data)
            return dict(item)

    def get_published(self, published_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            item = data["published"].get(published_id)
            return dict(item) if item else None

    def create_portfolio(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            data["portfolios"][portfolio["id"]] = portfolio
            self._write(data)
            return dict(portfolio)

    def get_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            item = data["portfolios"].get(portfolio_id)
            return dict(item) if item else None

    def list_portfolios(self, owner_uid: str) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            items = [dict(item) for item in data["portfolios"].values() if item.get("owner_uid") == owner_uid]
            items.sort(key=lambda item: item.get("updatedAt") or item.get("createdAt", ""), reverse=True)
            return items[:200]

    def update_portfolio(self, portfolio_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            item = data["portfolios"].get(portfolio_id)
            if not item:
                return None
            item.update(updates)
            data["portfolios"][portfolio_id] = item
            self._write(data)
            return dict(item)

    def delete_portfolio(self, owner_uid: str, portfolio_id: str) -> bool:
        with self._lock:
            data = self._read()
            item = data["portfolios"].get(portfolio_id)
            if not item or item.get("owner_uid") != owner_uid:
                return False
            del data["portfolios"][portfolio_id]
            self._write(data)
            return True

    def create_converter_upload(self, upload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            data["converter_uploads"][upload["id"]] = upload
            self._write(data)
            return dict(upload)

    def get_converter_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            item = data["converter_uploads"].get(upload_id)
            return dict(item) if item else None

    def list_converter_uploads(self, owner_uid: str) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            items = [dict(item) for item in data["converter_uploads"].values() if item.get("owner_uid") == owner_uid]
            items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
            return items

    def create_converter_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._read()
            data["converter_jobs"][job["id"]] = job
            self._write(data)
            return dict(job)

    def get_converter_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            item = data["converter_jobs"].get(job_id)
            return dict(item) if item else None

    def list_converter_jobs(self, owner_uid: str) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            jobs = [dict(item) for item in data["converter_jobs"].values() if item.get("owner_uid") == owner_uid]
            jobs.sort(key=lambda job: job.get("createdAt", ""), reverse=True)
            return jobs[:200]

    def list_all_converter_jobs(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            data = self._read()
            jobs = [dict(item) for item in data["converter_jobs"].values()]
            jobs.sort(key=lambda job: job.get("createdAt", ""), reverse=True)
            return jobs[:limit]

    def delete_converter_upload(self, upload_id: str) -> bool:
        with self._lock:
            data = self._read()
            if upload_id not in data["converter_uploads"]:
                return False
            del data["converter_uploads"][upload_id]
            self._write(data)
            return True

    def delete_converter_job(self, job_id: str) -> bool:
        with self._lock:
            data = self._read()
            if job_id not in data["converter_jobs"]:
                return False
            del data["converter_jobs"][job_id]
            self._write(data)
            return True


class FirestoreStore(BaseStore):
    mode = "firestore"

    def __init__(self, base_dir: Path):
        if firebase_admin is None or credentials is None or firestore is None:
            raise RuntimeError("firebase-admin is not installed.")

        cred_source = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()

        if cred_source:
            cred = credentials.Certificate(json.loads(cred_source))
        elif cred_path:
            path = Path(cred_path)
            if not path.is_absolute():
                path = base_dir / cred_path
            cred = credentials.Certificate(str(path))
        else:
            raise RuntimeError("Missing FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_PATH.")

        app_name = "viru-store"
        try:
            firebase_admin.get_app(app_name)
        except ValueError:
            firebase_admin.initialize_app(cred, name=app_name)

        self.db = firestore.client(firebase_admin.get_app(app_name))

    def _normalize(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        return json.loads(json.dumps(doc, ensure_ascii=True))

    def create_share(self, share_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        self.db.collection("shares").document(share_id).set(item)
        return self.get_share(share_id) or {}

    def get_share(self, share_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("shares").document(share_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        data["id"] = share_id
        return self._normalize(data)

    def update_share(self, share_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ref = self.db.collection("shares").document(share_id)
        snap = ref.get()
        if not snap.exists:
            return None
        ref.set(updates, merge=True)
        return self.get_share(share_id)

    def create_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        self.db.collection("projects").document(project["id"]).set(project)
        return self._normalize(project)

    def list_projects(self, owner_uid: str) -> List[Dict[str, Any]]:
        query = (
            self.db.collection("projects")
            .where("owner_uid", "==", owner_uid)
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(100)
        )
        items = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            data["id"] = data.get("id") or snap.id
            items.append(self._normalize(data))
        return items

    def delete_project(self, owner_uid: str, project_id: str) -> bool:
        ref = self.db.collection("projects").document(project_id)
        snap = ref.get()
        if not snap.exists:
            return False
        data = snap.to_dict() or {}
        if data.get("owner_uid") != owner_uid:
            return False
        ref.delete()
        return True

    def create_published(self, published_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
        self.db.collection("published").document(published_id).set(item)
        return self.get_published(published_id) or {}

    def get_published(self, published_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("published").document(published_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        data["id"] = published_id
        return self._normalize(data)

    def create_portfolio(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        self.db.collection("portfolios").document(portfolio["id"]).set(portfolio)
        return self._normalize(portfolio)

    def get_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("portfolios").document(portfolio_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        data["id"] = data.get("id") or portfolio_id
        return self._normalize(data)

    def list_portfolios(self, owner_uid: str) -> List[Dict[str, Any]]:
        query = (
            self.db.collection("portfolios")
            .where("owner_uid", "==", owner_uid)
            .order_by("updatedAt", direction=firestore.Query.DESCENDING)
            .limit(200)
        )
        items = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            data["id"] = data.get("id") or snap.id
            items.append(self._normalize(data))
        return items

    def update_portfolio(self, portfolio_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ref = self.db.collection("portfolios").document(portfolio_id)
        snap = ref.get()
        if not snap.exists:
            return None
        ref.set(updates, merge=True)
        return self.get_portfolio(portfolio_id)

    def delete_portfolio(self, owner_uid: str, portfolio_id: str) -> bool:
        ref = self.db.collection("portfolios").document(portfolio_id)
        snap = ref.get()
        if not snap.exists:
            return False
        data = snap.to_dict() or {}
        if data.get("owner_uid") != owner_uid:
            return False
        ref.delete()
        return True

    def create_converter_upload(self, upload: Dict[str, Any]) -> Dict[str, Any]:
        self.db.collection("converter_uploads").document(upload["id"]).set(upload)
        return self._normalize(upload)

    def get_converter_upload(self, upload_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("converter_uploads").document(upload_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        data["id"] = upload_id
        return self._normalize(data)

    def list_converter_uploads(self, owner_uid: str) -> List[Dict[str, Any]]:
        query = (
            self.db.collection("converter_uploads")
            .where("owner_uid", "==", owner_uid)
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(200)
        )
        items = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            data["id"] = data.get("id") or snap.id
            items.append(self._normalize(data))
        return items

    def create_converter_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        self.db.collection("converter_jobs").document(job["id"]).set(job)
        return self._normalize(job)

    def get_converter_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        snap = self.db.collection("converter_jobs").document(job_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        data["id"] = job_id
        return self._normalize(data)

    def list_converter_jobs(self, owner_uid: str) -> List[Dict[str, Any]]:
        query = (
            self.db.collection("converter_jobs")
            .where("owner_uid", "==", owner_uid)
            .order_by("createdAt", direction=firestore.Query.DESCENDING)
            .limit(200)
        )
        items = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            data["id"] = data.get("id") or snap.id
            items.append(self._normalize(data))
        return items

    def list_all_converter_jobs(self, limit: int = 200) -> List[Dict[str, Any]]:
        query = self.db.collection("converter_jobs").order_by("createdAt", direction=firestore.Query.DESCENDING).limit(limit)
        items = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            data["id"] = data.get("id") or snap.id
            items.append(self._normalize(data))
        return items

    def delete_converter_upload(self, upload_id: str) -> bool:
        ref = self.db.collection("converter_uploads").document(upload_id)
        snap = ref.get()
        if not snap.exists:
            return False
        ref.delete()
        return True

    def delete_converter_job(self, job_id: str) -> bool:
        ref = self.db.collection("converter_jobs").document(job_id)
        snap = ref.get()
        if not snap.exists:
            return False
        ref.delete()
        return True


def build_store(base_dir: Path) -> BaseStore:
    prefer_firestore = os.getenv("PERSISTENCE_PROVIDER", "firestore").strip().lower() == "firestore"
    if prefer_firestore:
        try:
            return FirestoreStore(base_dir)
        except Exception:
            pass
    return JsonFileStore(base_dir / "data" / "storage.json")
