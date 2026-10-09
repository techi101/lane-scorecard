"""Collection follow-through: a recorded fix needs subsequent human evidence.

This is an operational checklist, not a causal impact estimate. Reviews are
snapshots: every read derives their validity from the current observations.
"""
import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from .scoring import today


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Start(Payload):
    floor_id: str = Field(min_length=1, max_length=80)


class Intervention(Payload):
    revision: int = Field(ge=1)
    date: date
    owner_role: str = Field(min_length=1, max_length=80)
    note: str = Field(min_length=1, max_length=500)
    due_date: date


class Review(Payload):
    revision: int = Field(ge=1)
    evidence_signature: str = Field(pattern=r"^[a-f0-9]{64}$")
    human_confirmed: Literal[True]


def stamp():
    return datetime.now(timezone.utc).isoformat()


def evidence_row(check):
    # Deliberately exclude photos and observation notes.
    return {"id": check["id"], "date": check["date"], "round": check["round"],
            "kept_separate": check.get("kept_separate"),
            "human_confirmed": check.get("human_confirmed") is True,
            "reporter": check.get("reporter", "operator"), "source": check.get("source"),
            "version": check.get("evidence_version", check.get("updated_at", check.get("created_at")))}


def view(record, checks, as_of=None):
    as_of = as_of or today()
    intervention = record.get("intervention")
    rows = sorted((evidence_row(c) for c in checks
                   if intervention and c["floor_id"] == record["floor_id"]
                   and intervention["date"] < c["date"] <= as_of.isoformat()),
                  key=lambda c: (c["date"], c["round"], c["id"]))
    signature = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    separated = [r for r in rows if r["human_confirmed"] and r["kept_separate"] is True]
    mixed = [r for r in rows if r["kept_separate"] is False]
    days = sorted({r["date"] for r in separated})
    fresh = bool(days and days[-1] >= (as_of - timedelta(days=7)).isoformat())
    eligible = bool(intervention and len(days) >= 3 and not mixed and fresh)
    review = record.get("review")
    if not intervention:
        status = "open"
    elif review and (review["evidence_signature"] != signature or not eligible):
        status = "review_needed"
    elif review:
        status = "reviewed"
    elif mixed:
        status = "mixing_observed"
    elif eligible:
        status = "ready_for_review"
    else:
        status = "awaiting_checks"
    return {**record, "status": status, "can_review": eligible and status != "reviewed",
            "evidence": rows, "evidence_signature": signature,
            "separated_days": len(days), "separated_checks": len(separated),
            "mixed_checks": len(mixed), "unknown_checks": len(rows) - len(separated) - len(mixed),
            "fresh": fresh, "required_days": 3,
            "overdue": bool(intervention and intervention["due_date"] < as_of.isoformat() and status != "reviewed")}


def register_routes(app, store, authenticated, audit):
    workspace_type = Literal["demo", "pilot"]

    def checks(workspace):
        return store.list(f"{workspace}:checks")

    def load(workspace, floor_id, revision):
        record = store.get(f"{workspace}:followups", floor_id)
        if not record or not store.get(f"{workspace}:floors", floor_id):
            raise HTTPException(404, "Collection action not found.")
        if revision != record["revision"]:
            raise HTTPException(409, "This action changed. Reload the plan before saving.")
        if len(record["history"]) >= 100:
            raise HTTPException(409, "This action has reached the pilot limit of 100 updates.")
        return record

    def save(workspace, old, new, action):
        new["revision"] = old["revision"] + 1
        if not store.replace_if_unchanged(f"{workspace}:followups", old["id"], old, new):
            raise HTTPException(409, "This action changed. Reload the plan before saving.")
        audit(workspace, action, old["id"])
        return view(new, checks(workspace))

    @app.get("/api/{workspace}/followups")
    def list_followups(workspace: workspace_type, _=Depends(authenticated)):
        observations = checks(workspace)
        floors = {f["id"]: f["name"] for f in store.list(f"{workspace}:floors")}
        return sorted(({**view(r, observations), "name": floors[r["floor_id"]]}
                       for r in store.list(f"{workspace}:followups") if r["floor_id"] in floors),
                      key=lambda r: r["name"].casefold())

    @app.post("/api/{workspace}/followups", status_code=201)
    def start_followup(workspace: workspace_type, payload: Start, _=Depends(authenticated)):
        if not store.get(f"{workspace}:floors", payload.floor_id):
            raise HTTPException(404, "Choose an existing floor.")
        observations = checks(workspace)
        failures = [c for c in observations if c["floor_id"] == payload.floor_id
                    and c.get("kept_separate") is False and c["date"] <= today().isoformat()]
        if not failures:
            raise HTTPException(422, "Record an observed collection mixing problem first.")
        latest = max(failures, key=lambda c: (c["date"], c["id"]))
        at = stamp()
        value = {"id": payload.floor_id, "floor_id": payload.floor_id, "revision": 1,
                 "created_at": at, "source": "simulated" if workspace == "demo" else "real pilot",
                 "baseline": evidence_row(latest), "intervention": None, "review": None,
                 "history": [{"event": "opened", "at": at}]}
        if not store.put(f"{workspace}:followups", value["id"], value, create=True):
            raise HTTPException(409, "This floor already has a collection action. Open its tracker.")
        audit(workspace, "collection_action_opened", value["id"])
        return view(value, observations)

    @app.put("/api/{workspace}/followups/{floor_id}/intervention")
    def record_intervention(workspace: workspace_type, floor_id: str, payload: Intervention,
                            _=Depends(authenticated)):
        old = load(workspace, floor_id, payload.revision)
        earliest = max(old["baseline"]["date"], (old.get("intervention") or {}).get("date", ""))
        if payload.date > today() or payload.date.isoformat() < earliest or payload.date < today() - timedelta(days=365):
            raise HTTPException(422, "Use a fix date on or after the recorded problem and previous fix, no later than today, within the last year.")
        if not payload.date <= payload.due_date <= today() + timedelta(days=90):
            raise HTTPException(422, "Review due date must follow the fix and be within the next 90 days.")
        intervention = payload.model_dump(mode="json", exclude={"revision"})
        at = stamp()
        new = {**old, "intervention": intervention, "review": None,
               "history": [*old["history"], {"event": "fix_recorded", "at": at, **intervention}]}
        return save(workspace, old, new, "collection_fix_recorded")

    @app.post("/api/{workspace}/followups/{floor_id}/review")
    def review_followup(workspace: workspace_type, floor_id: str, payload: Review,
                        _=Depends(authenticated)):
        old = load(workspace, floor_id, payload.revision)
        current = view(old, checks(workspace))
        if payload.evidence_signature != current["evidence_signature"]:
            raise HTTPException(409, "Observations changed. Reload and review the current evidence.")
        if not current["can_review"]:
            raise HTTPException(422, "Review needs separation on 3 distinct days after the fix, no mixing since it, and a separated check within 7 days.")
        review = {"at": stamp(), "evidence_signature": current["evidence_signature"],
                  "separated_days": current["separated_days"]}
        new = {**old, "review": review,
               "history": [*old["history"], {"event": "reviewed", **review}]}
        return save(workspace, old, new, "collection_action_reviewed")
