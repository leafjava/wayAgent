"""项目/资料/版本数据模型与 SQLite 存储。"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _hash_canonical(payload: Dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "0x" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_text(text: str) -> str:
    return "0x" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Project:
    projectId: str
    name: str
    symbol: str
    sector: str
    description: str
    website: str = ""
    whitepaper: str = ""
    createdAt: int = field(default_factory=_now_ts)


@dataclass
class Document:
    docId: str
    projectId: str
    docType: str  # whitepaper / announcement / unlock / tokenomics / news / community
    title: str
    content: str
    source: str = "internal"
    sourceUrl: str = ""
    trustLevel: str = "official"  # official / market / news / community / ai
    createdAt: int = field(default_factory=_now_ts)


@dataclass
class Version:
    versionId: str
    projectId: str
    docType: str
    version: str
    contentHash: str
    content: str
    parentVersion: Optional[str] = None
    changes: Dict[str, Any] = field(default_factory=dict)
    createdAt: int = field(default_factory=_now_ts)


class ProjectStore:
    """项目/资料/版本的 SQLite 存储。"""

    def __init__(self, database: str) -> None:
        self.database = str(Path(database))
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.database, timeout=10)
        c.row_factory = sqlite3.Row
        return c

    def _init(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    sector TEXT,
                    description TEXT,
                    website TEXT,
                    whitepaper TEXT,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    source_url TEXT,
                    trust_level TEXT,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id, doc_type);
                CREATE TABLE IF NOT EXISTS versions (
                    version_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    version TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    parent_version TEXT,
                    changes_json TEXT,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_versions_project ON versions(project_id, doc_type, created_at DESC);
                CREATE TABLE IF NOT EXISTS risk_states (
                    project_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    score REAL NOT NULL,
                    factors_json TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS watchlist (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    note TEXT,
                    budget REAL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS consents (
                    consent_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    user_label TEXT,
                    created_at INTEGER NOT NULL,
                    evidence_hash TEXT,
                    chain_status TEXT NOT NULL DEFAULT 'pending',
                    tx_hash TEXT
                );
                """
            )

    # ---------------- Projects ----------------
    def upsert_project(self, project: Project) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO projects(project_id,name,symbol,sector,description,website,whitepaper,created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (project.projectId, project.name, project.symbol, project.sector,
                 project.description, project.website, project.whitepaper, project.createdAt),
            )

    def list_projects(self) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
        return [self._row_project(r) for r in rows]

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        return self._row_project(r) if r else None

    # ---------------- Documents ----------------
    def add_document(self, doc: Document) -> str:
        doc_id = doc.docId or uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO documents(doc_id,project_id,doc_type,title,content,source,source_url,trust_level,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (doc_id, doc.projectId, doc.docType, doc.title, doc.content,
                 doc.source, doc.sourceUrl, doc.trustLevel, doc.createdAt),
            )
        return doc_id

    def list_documents(self, project_id: str, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._conn() as c:
            if doc_type:
                rows = c.execute(
                    "SELECT * FROM documents WHERE project_id=? AND doc_type=? ORDER BY created_at DESC",
                    (project_id, doc_type),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM documents WHERE project_id=? ORDER BY created_at DESC",
                    (project_id,),
                ).fetchall()
        return [self._row_document(r) for r in rows]

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM documents WHERE doc_id=?", (doc_id,)).fetchone()
        return self._row_document(r) if r else None

    # ---------------- Versions ----------------
    def add_version(self, v: Version) -> str:
        v_id = v.versionId or uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO versions(version_id,project_id,doc_type,version,content_hash,content,parent_version,changes_json,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (v_id, v.projectId, v.docType, v.version, v.contentHash, v.content,
                 v.parentVersion, json.dumps(v.changes, ensure_ascii=False), v.createdAt),
            )
        return v_id

    def list_versions(self, project_id: str, doc_type: str) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM versions WHERE project_id=? AND doc_type=? ORDER BY created_at DESC",
                (project_id, doc_type),
            ).fetchall()
        return [self._row_version(r) for r in rows]

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM versions WHERE version_id=?", (version_id,)).fetchone()
        return self._row_version(r) if r else None

    def latest_version(self, project_id: str, doc_type: str) -> Optional[Dict[str, Any]]:
        versions = self.list_versions(project_id, doc_type)
        return versions[0] if versions else None

    # ---------------- Risk state ----------------
    def upsert_risk(self, project_id: str, status: str, score: float, factors: Dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO risk_states(project_id,status,score,factors_json,updated_at)
                   VALUES(?,?,?,?,?)""",
                (project_id, status, score, json.dumps(factors, ensure_ascii=False), _now_ts()),
            )

    def get_risk(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            r = c.execute("SELECT * FROM risk_states WHERE project_id=?", (project_id,)).fetchone()
        if not r:
            return None
        result = dict(r)
        result["factors"] = json.loads(result.pop("factors_json"))
        return result

    # ---------------- Watchlist ----------------
    def add_watch(self, project_id: str, note: str = "", budget: float = 0.0) -> str:
        wid = uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                "INSERT INTO watchlist(id,project_id,note,budget,created_at) VALUES(?,?,?,?,?)",
                (wid, project_id, note, budget, _now_ts()),
            )
        return wid

    def list_watch(self) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM watchlist ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def remove_watch(self, watch_id: str) -> bool:
        with self._conn() as c:
            cur = c.execute("DELETE FROM watchlist WHERE id=?", (watch_id,))
        return cur.rowcount > 0

    # ---------------- Consents (授权执行) ----------------
    def add_consent(self, project_id: str, platform: str, action_type: str,
                    user_label: str = "", evidence_hash: str = "") -> Dict[str, Any]:
        consent_id = uuid.uuid4().hex
        with self._conn() as c:
            c.execute(
                """INSERT INTO consents(consent_id,project_id,platform,action_type,user_label,created_at,evidence_hash,chain_status)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (consent_id, project_id, platform, action_type, user_label,
                 _now_ts(), evidence_hash, "pending"),
            )
        return {
            "consentId": consent_id,
            "projectId": project_id,
            "platform": platform,
            "actionType": action_type,
            "userLabel": user_label,
            "evidenceHash": evidence_hash,
            "chainStatus": "pending",
            "createdAt": _now_ts(),
        }

    def list_consents(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._conn() as c:
            if project_id:
                rows = c.execute(
                    "SELECT * FROM consents WHERE project_id=? ORDER BY created_at DESC",
                    (project_id,),
                ).fetchall()
            else:
                rows = c.execute("SELECT * FROM consents ORDER BY created_at DESC").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            results.append(d)
        return results

    def update_consent_chain(self, consent_id: str, tx_hash: str, status: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE consents SET tx_hash=?, chain_status=? WHERE consent_id=?",
                (tx_hash, status, consent_id),
            )

    # ---------------- Row conversions ----------------
    @staticmethod
    def _row_project(r: sqlite3.Row) -> Dict[str, Any]:
        d = dict(r)
        return {
            "projectId": d.pop("project_id"),
            "name": d.pop("name"),
            "symbol": d.pop("symbol"),
            "sector": d.pop("sector") or "",
            "description": d.pop("description") or "",
            "website": d.pop("website") or "",
            "whitepaper": d.pop("whitepaper") or "",
            "createdAt": d.pop("created_at"),
        }

    @staticmethod
    def _row_document(r: sqlite3.Row) -> Dict[str, Any]:
        d = dict(r)
        return {
            "docId": d.pop("doc_id"),
            "projectId": d.pop("project_id"),
            "docType": d.pop("doc_type"),
            "title": d.pop("title"),
            "content": d.pop("content"),
            "source": d.pop("source") or "",
            "sourceUrl": d.pop("source_url") or "",
            "trustLevel": d.pop("trust_level") or "official",
            "createdAt": d.pop("created_at"),
        }

    @staticmethod
    def _row_version(r: sqlite3.Row) -> Dict[str, Any]:
        d = dict(r)
        return {
            "versionId": d.pop("version_id"),
            "projectId": d.pop("project_id"),
            "docType": d.pop("doc_type"),
            "version": d.pop("version"),
            "contentHash": d.pop("content_hash"),
            "content": d.pop("content"),
            "parentVersion": d.pop("parent_version"),
            "changes": json.loads(d.pop("changes_json") or "{}"),
            "createdAt": d.pop("created_at"),
        }


def hash_project_payload(payload: Dict[str, Any]) -> str:
    return _hash_canonical(payload)


def hash_text(text: str) -> str:
    return _hash_text(text)
