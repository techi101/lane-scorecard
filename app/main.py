import base64
import csv
import hashlib
import io
import os
import random
import secrets
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .scoring import STREAMS, card_data, community_goal, deep_check_plan, summarize, today, location_order
from .guide import build as build_guide, items_from_text, read_receipt
from .storage import Store
from .vision import sanitize, suggest
from .actions import weekly_actions
from .report import render_report
from .followups import register_routes as register_followups

ROOT = Path(__file__).resolve().parent.parent
Workspace = Literal["demo", "pilot"]
MAX_LOCATIONS = 200  # a whole campus, not one hostel
DEMO_LOCATIONS = [  # (name, area) for the simulated campus demo
    ("Academic block 1 · entrance", "Academic blocks"), ("Library · entrance", "Library"),
    ("Main canteen · front", "Canteen & food"), ("Nescafe kiosk", "Canteen & food"),
    ("Boys hostel · gate", "Hostels"), ("Sports complex · track", "Sports"),
]
Rating = Literal["clean", "few", "mixed", "unseen"]
Issue = Literal["plastic_in_wet", "food_in_dry", "hidden_below", "one_bag"]  # keys of scoring.ISSUES
SeenRating = Literal["clean", "few", "mixed"]


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(StrictModel):
    code: str = Field(min_length=1, max_length=200)


class Floor(StrictModel):
    name: str = Field(min_length=1, max_length=60)
    # Campus area the bin pair belongs to, e.g. "Academic blocks", "Hostels". Optional; empty means "Other".
    area: str = Field(default="", max_length=40)
    permission: bool


class Check(StrictModel):
    floor_id: str = Field(min_length=1, max_length=80)
    date: date
    # "collection" is the round a sanitation worker reports from at pickup.
    round: Literal["morning", "evening", "collection"]
    bio: Rating
    nonbio: Rating
    # Optional SWM 2026 streams. None = no such bin here / not part of this check.
    sanitary: Rating | None = None
    special: Rating | None = None
    # Deep check: the checker looked below the top layer, not just at the surface.
    deep: bool = False
    kept_separate: bool | None = None
    hazard: bool | None = None
    issues: list[Issue] = Field(default_factory=list, max_length=3)
    note: str = Field(default="", max_length=500)
    photos: list[str] = Field(default_factory=list, max_length=2)
    human_confirmed: Literal[True]

    @field_validator("issues")
    @classmethod
    def unique_issues(cls, value):
        return sorted(set(value))

    @field_validator("date")
    @classmethod
    def date_in_past(cls, value):
        if value > today():
            raise ValueError("Checks cannot be dated in the future.")
        if value < today() - timedelta(days=365):
            raise ValueError("Checks must be within the last year.")
        return value


class Photo(StrictModel):
    image: str = Field(max_length=2_800_000)
    stream: Literal["bio", "nonbio"]
    permission: Literal[True]


class GuideRequest(StrictModel):
    """A receipt as pasted text and/or a photo. Never stored."""
    text: str = Field(default="", max_length=6000)
    image: str = Field(default="", max_length=2_800_000)


class CardRequest(StrictModel):
    end: date


class WorkerReport(StrictModel):
    """What a worker can tap at pickup. Always today, always the collection round."""
    floor_id: str = Field(min_length=1, max_length=80)
    bio: Literal["clean", "few", "mixed"]
    nonbio: Literal["clean", "few", "mixed"]
    sanitary: SeenRating | None = None
    special: SeenRating | None = None
    deep: bool = False
    hazard: bool = False
    issues: list[Issue] = Field(default_factory=list, max_length=3)

    @field_validator("issues")
    @classmethod
    def unique_issues(cls, value):
        return sorted(set(value))


def seed_demo(store):
    if store.get("meta", "demo-seeded-campus"):
        return
    # Replace the older hostel-floor demo, if present. Only generated rows are touched; locations
    # people added to the demo themselves are kept.
    if store.get("meta", "demo-seeded"):
        generated = {f"demo-floor-{i}" for i in range(len(DEMO_LOCATIONS))}
        for check in store.list("demo:checks"):
            if check["floor_id"] in generated:
                store.delete("demo:checks", check["id"])
        for fid in generated:
            store.delete("demo:floors", fid)
        for card in store.list("cards"):
            if card["workspace"] == "demo":
                store.delete("cards", digest(card["token"]))
                store.delete("card-index", card["index"])
    rng = random.Random(101)
    floors, checks = [], []
    for i, (name, area) in enumerate(DEMO_LOCATIONS):
        fid = f"demo-floor-{i}"
        floors.append({"id": fid, "name": name, "area": area, "permission": True, "created_at": now()})
        for ago in range(27, -1, -1):
            day = (today() - timedelta(days=ago)).isoformat()
            cid = f"{day}:{fid}:morning"
            choices = ["clean", "few", "mixed", "unseen"]
            weights = [max(20, 64 - ago - i * 3), 24, 12 + i * 2, 4]
            checks.append({"id": cid, "floor_id": fid, "date": day, "round": "morning", "bio": rng.choices(choices, weights)[0], "nonbio": rng.choices(choices, weights)[0], "kept_separate": rng.random() > .12, "note": "Generated example — not a real observation.", "photos": [], "human_confirmed": True, "created_at": now(), "source": "simulated"})
    store.put_many("demo:floors", floors)
    store.put_many("demo:checks", checks)
    store.put("meta", "demo-seeded", {"at": now()})
    store.put("meta", "demo-seeded-campus", {"at": now()})


def make_card(store, workspace, floor_id, end):
    floors = store.list(f"{workspace}:floors")
    if not any(f["id"] == floor_id for f in floors):
        raise HTTPException(404, "Floor not found.")
    report = summarize(floors, store.list(f"{workspace}:checks"), end)
    value = card_data(report, floor_id)
    if not value["checks"]:
        raise HTTPException(409, "Record at least one check in this week before creating a card.")
    # Stable per-floor/week link, refreshed by explicit generation or the schedule.
    key = f"{workspace}:{floor_id}:{end.isoformat()}"
    token_record = store.get("card-index", key)
    token = token_record["token"] if token_record else secrets.token_urlsafe(32)
    snapshot = {**value, "workspace": workspace, "source": "simulated" if workspace == "demo" else "real pilot", "generated_at": now(), "token": token, "index": key}
    store.put("cards", digest(token), snapshot)
    store.put("card-index", key, {"token": token, "workspace": workspace})
    return snapshot


def scheduled_cards(store):
    end = today() - timedelta(days=1)
    generated = 0
    for floor in store.list("pilot:floors"):
        try:
            make_card(store, "pilot", floor["id"], end)
            generated += 1
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
    return {"generated": generated, "end": end.isoformat()}


def create_app(directory=None):
    directory = Path(directory or os.getenv("LANE_DATA_DIR", str(ROOT / ".local")))
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory)
    admin_code = os.getenv("LANE_ADMIN_CODE")
    if not admin_code:
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            raise RuntimeError("Set LANE_ADMIN_CODE for cloud deployment.")
        code_file = directory / "admin-code.txt"
        if not code_file.exists():
            code_file.write_text(secrets.token_urlsafe(24), encoding="utf-8")
        admin_code = code_file.read_text(encoding="utf-8").strip()
    if len(admin_code) < 24:
        raise RuntimeError("Use an operator access code of at least 24 characters.")
    secure = os.getenv("LANE_SECURE_COOKIE") == "1"
    bucket = os.getenv("LANE_PHOTO_BUCKET")
    attempts = defaultdict(deque)
    seed_demo(store)
    app = FastAPI(title="Lane Scorecard", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store = store
    app.state.directory = directory

    @app.middleware("http")
    async def guard(request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            if request.headers.get("x-lane-request") != "1":
                return JSONResponse({"detail": "Missing request protection header."}, status_code=403)
            origin = request.headers.get("origin")
            allowed = os.getenv("LANE_ORIGIN") or str(request.base_url).rstrip("/")
            if origin and origin != allowed:
                return JSONResponse({"detail": "Cross-origin writes are blocked."}, status_code=403)
            try:
                size = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "Invalid request length."}, status_code=400)
            if size > 3_000_000:
                return JSONResponse({"detail": "Request is too large."}, status_code=413)
            body = await request.body()
            if len(body) > 3_000_000:
                return JSONResponse({"detail": "Request is too large."}, status_code=413)
        response = await call_next(request)
        response.headers.update({
            "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY", "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
            "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
        })
        return response

    # View-only access: anyone may read both workspaces without signing in, so judges and visitors can
    # see the real pilot. Every change still needs the operator code. LANE_PUBLIC_VIEW=0 turns this off.
    public_view = os.getenv("LANE_PUBLIC_VIEW", "1") != "0"

    def operator(request: Request):
        token = request.cookies.get("lane_session", "")
        session = store.get("sessions", digest(token)) if token else None
        if not session or session["expires"] < time.time():
            if session:
                store.delete("sessions", digest(token))
            raise HTTPException(401, "Sign in with your operator access code.")
        return session

    def authenticated(request: Request):
        try:
            return operator(request)
        except HTTPException:
            if public_view and request.method in ("GET", "HEAD"):
                return {"guest": True}
            raise

    def audit(workspace, action, entity):
        record = {"id": str(uuid4()), "at": now(), "action": action, "entity": entity}
        store.put(f"{workspace}:audit", record["id"], record)

    def invalidate_cards(workspace):
        for card in store.list("cards"):
            if card["workspace"] == workspace:
                store.delete("cards", digest(card["token"]))
                store.delete("card-index", card["index"])

    def photo_delete(workspace, photo_id):
        photo = store.get(f"{workspace}:photos", photo_id)
        if not photo:
            return
        if bucket:
            import boto3
            boto3.client("s3").delete_object(Bucket=bucket, Key=f"{workspace}/{photo_id}.jpg")
        else:
            (directory / "photos" / f"{photo_id}.jpg").unlink(missing_ok=True)
        store.delete(f"{workspace}:photos", photo_id)

    @app.get("/api/health")
    def health():
        return {"ok": True, "storage": "dynamodb" if store.table else "sqlite", "ai_configured": os.getenv("LANE_ENABLE_AI") == "1", "today": today().isoformat()}

    @app.post("/api/login")
    def login(payload: Login, request: Request, response: Response):
        ip = request.client.host if request.client else "unknown"
        recent = attempts[ip]
        while recent and recent[0] < time.monotonic() - 300:
            recent.popleft()
        if len(recent) >= 10:
            raise HTTPException(429, "Too many attempts. Wait five minutes before trying again.")
        recent.append(time.monotonic())
        if not secrets.compare_digest(payload.code.encode(), admin_code.encode()):
            raise HTTPException(401, "That access code is not correct.")
        recent.clear()
        token = secrets.token_urlsafe(32)
        store.put("sessions", digest(token), {"key": digest(token), "expires": time.time() + 12 * 3600})
        response.set_cookie("lane_session", token, httponly=True, secure=secure, samesite="strict", max_age=12 * 3600, path="/")
        return {"ok": True}

    @app.get("/api/session")
    def session(_=Depends(operator)):
        return {"ok": True}

    @app.get("/api/viewer")
    def viewer(request: Request):
        try:
            operator(request)
            signed_in = True
        except HTTPException:
            signed_in = False
        latest = {ws: max((c["date"] for c in store.list(f"{ws}:checks")), default=None) for ws in ("demo", "pilot")}
        return {"operator": signed_in, "public_view": public_view, "latest": latest}

    @app.post("/api/logout")
    def logout(request: Request, response: Response):
        store.delete("sessions", digest(request.cookies.get("lane_session", "")))
        response.delete_cookie("lane_session", path="/")
        return {"ok": True}

    @app.get("/api/{workspace}/floors")
    def floors(workspace: Workspace, _=Depends(authenticated)):
        return store.list(f"{workspace}:floors")

    @app.post("/api/{workspace}/floors", status_code=201)
    def add_floor(workspace: Workspace, payload: Floor, _=Depends(authenticated)):
        if not payload.permission:
            raise HTTPException(422, "Confirm permission before adding a floor.")
        existing = store.list(f"{workspace}:floors")
        if len(existing) >= MAX_LOCATIONS:
            raise HTTPException(409, f"This pilot supports up to {MAX_LOCATIONS} bin locations.")
        if any(f["name"].casefold() == payload.name.casefold() for f in existing):
            raise HTTPException(409, "A floor with this name already exists.")
        value = {**payload.model_dump(), "id": str(uuid4()), "created_at": now()}
        store.put(f"{workspace}:floors", value["id"], value)
        audit(workspace, "floor_added", value["id"])
        return value

    @app.put("/api/{workspace}/floors/{floor_id}")
    def rename_floor(workspace: Workspace, floor_id: str, payload: Floor, _=Depends(authenticated)):
        """Change a location's name or area. Its checks and photos stay attached."""
        current = store.get(f"{workspace}:floors", floor_id)
        if not current:
            raise HTTPException(404, "Location not found.")
        if not payload.permission:
            raise HTTPException(422, "Confirm permission for this location.")
        if any(f["id"] != floor_id and f["name"].casefold() == payload.name.casefold() for f in store.list(f"{workspace}:floors")):
            raise HTTPException(409, "A location with this name already exists.")
        value = {**current, "name": payload.name, "area": payload.area, "updated_at": now()}
        store.put(f"{workspace}:floors", floor_id, value)
        invalidate_cards(workspace)  # cards show the old name
        audit(workspace, "floor_renamed", floor_id)
        return value

    @app.delete("/api/{workspace}/floors/{floor_id}")
    def delete_floor(workspace: Workspace, floor_id: str, _=Depends(authenticated)):
        if not store.get(f"{workspace}:floors", floor_id):
            raise HTTPException(404, "Floor not found.")
        for check in store.list(f"{workspace}:checks"):
            if check["floor_id"] == floor_id:
                for pid in check["photos"]:
                    photo_delete(workspace, pid)
                store.delete(f"{workspace}:checks", check["id"])
        store.delete(f"{workspace}:followups", floor_id)
        store.delete(f"{workspace}:floors", floor_id)
        invalidate_cards(workspace)
        audit(workspace, "floor_deleted", floor_id)
        return {"ok": True}

    def save_check(workspace, payload, updating=None):
        if not store.get(f"{workspace}:floors", payload.floor_id):
            raise HTTPException(404, "Choose an existing floor.")
        if len(set(payload.photos)) != len(payload.photos):
            raise HTTPException(422, "A photo can only be attached once.")
        photo_streams = []
        for pid in payload.photos:
            photo = store.get(f"{workspace}:photos", pid)
            if not photo:
                raise HTTPException(422, "One of the photos was not found in this workspace.")
            photo_streams.append(photo["stream"])
        if len(photo_streams) != len(set(photo_streams)):
            raise HTTPException(422, "Attach at most one photo for each bin.")
        cid = f"{payload.date.isoformat()}:{payload.floor_id}:{payload.round}"
        previous = store.get(f"{workspace}:checks", cid)
        if updating and (updating != cid or not previous):
            raise HTTPException(409, "A correction must keep the original floor, date and round.")
        # A photo must belong to a single observation to keep evaluation honest.
        for existing in store.list(f"{workspace}:checks"):
            if existing["id"] != cid and set(existing["photos"]) & set(payload.photos):
                raise HTTPException(409, "This photo is already attached to another check.")
        value = {**payload.model_dump(mode="json"), "id": cid, "created_at": previous["created_at"] if previous else now(), "updated_at": now(), "source": "simulated" if workspace == "demo" else "real pilot"}
        value["evidence_version"] = str(uuid4())
        if previous and previous.get("reporter"):
            # An operator correction keeps who reported it and any hazard flag the form does not show.
            value["reporter"] = previous["reporter"]
            if value["hazard"] is None:
                value["hazard"] = previous.get("hazard")
        if not store.put(f"{workspace}:checks", cid, value, create=not bool(updating)):
            raise HTTPException(409, "This floor already has a check for that date and round. Edit it in the observation log.")
        if updating:
            for pid in set(previous["photos"]) - set(payload.photos):
                photo_delete(workspace, pid)
            invalidate_cards(workspace)
        audit(workspace, "check_corrected" if updating else "check_added", cid)
        return value

    @app.post("/api/{workspace}/checks", status_code=201)
    def add_check(workspace: Workspace, payload: Check, _=Depends(authenticated)):
        return save_check(workspace, payload)

    @app.put("/api/{workspace}/checks/{check_id}")
    def edit_check(workspace: Workspace, check_id: str, payload: Check, _=Depends(authenticated)):
        return save_check(workspace, payload, updating=check_id)

    @app.delete("/api/{workspace}/checks/{check_id}")
    def delete_check(workspace: Workspace, check_id: str, _=Depends(authenticated)):
        value = store.get(f"{workspace}:checks", check_id)
        if not value:
            raise HTTPException(404, "Check not found.")
        for pid in value["photos"]:
            photo_delete(workspace, pid)
        store.delete(f"{workspace}:checks", check_id)
        invalidate_cards(workspace)
        audit(workspace, "check_deleted", check_id)
        return {"ok": True}

    @app.get("/api/{workspace}/dashboard")
    def dashboard(workspace: Workspace, end: date | None = None, _=Depends(authenticated)):
        end = end or today()
        floor_rows, check_rows = store.list(f"{workspace}:floors"), store.list(f"{workspace}:checks")
        report = summarize(floor_rows, check_rows, end)
        previous = summarize(floor_rows, check_rows, end - timedelta(days=7))
        trend = []
        for week in range(3, -1, -1):
            item = summarize(floor_rows, check_rows, end - timedelta(days=7 * week))
            trend.append({k: item[k] for k in ["start", "end", "score", "both_clean_rate", "checks"]})
        selected = [c for c in check_rows if report["start"] <= c["date"] <= report["end"]]
        photos = {p["id"]: p for p in store.list(f"{workspace}:photos")}
        evaluation = {s: {"total": 0, "matched": 0} for s in STREAMS}
        for check in selected:
            for pid in check["photos"]:
                photo = photos.get(pid)
                if photo and photo["suggestion"]["status"] == "available":
                    item = evaluation[photo["stream"]]
                    item["total"] += 1
                    item["matched"] += int(photo["suggestion"]["rating"] == check[photo["stream"]])
        return {**report, "workspace": workspace, "previous": previous, "trend": trend,
                "recent": sorted(selected, key=lambda c: (c["date"], c["round"]), reverse=True),
                "evaluation": evaluation, "actions": weekly_actions(report, check_rows, previous),
                "deep_plan": deep_check_plan(floor_rows, check_rows, end, admin_code),
                "goal": community_goal(floor_rows, check_rows, end),
                "ai_configured": os.getenv("LANE_ENABLE_AI") == "1"}

    @app.post("/api/{workspace}/photos", status_code=201)
    def upload(workspace: Workspace, payload: Photo, _=Depends(authenticated)):
        try:
            raw = sanitize(base64.b64decode(payload.image, validate=True))
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        pid = str(uuid4())
        if bucket:
            import boto3
            boto3.client("s3").put_object(Bucket=bucket, Key=f"{workspace}/{pid}.jpg", Body=raw, ContentType="image/jpeg", ServerSideEncryption="AES256")
        else:
            path = directory / "photos"
            path.mkdir(exist_ok=True)
            (path / f"{pid}.jpg").write_bytes(raw)
        value = {"id": pid, "stream": payload.stream, "suggestion": suggest(raw, payload.stream), "created_at": now()}
        store.put(f"{workspace}:photos", pid, value)
        return value

    @app.get("/api/{workspace}/photos/{photo_id}")
    def get_photo(workspace: Workspace, photo_id: str, _=Depends(authenticated)):
        if not store.get(f"{workspace}:photos", photo_id):
            raise HTTPException(404, "Photo not found.")
        if bucket:
            import boto3
            result = boto3.client("s3").get_object(Bucket=bucket, Key=f"{workspace}/{photo_id}.jpg")
            return Response(result["Body"].read(), media_type="image/jpeg")
        return FileResponse(directory / "photos" / f"{photo_id}.jpg", media_type="image/jpeg")

    @app.delete("/api/{workspace}/photos/{photo_id}")
    def remove_unused_photo(workspace: Workspace, photo_id: str, _=Depends(authenticated)):
        if any(photo_id in c["photos"] for c in store.list(f"{workspace}:checks")):
            raise HTTPException(409, "Remove the photo from its check first.")
        photo_delete(workspace, photo_id)
        return {"ok": True}

    @app.get("/api/{workspace}/photos")
    def list_photos(workspace: Workspace, _=Depends(authenticated)):
        """Every photo in the workspace with the check it belongs to, newest first."""
        names = {f["id"]: (f["name"], f.get("area", "")) for f in store.list(f"{workspace}:floors")}
        owner = {pid: c for c in store.list(f"{workspace}:checks") for pid in c["photos"]}
        rows = []
        for p in store.list(f"{workspace}:photos"):
            c = owner.get(p["id"])
            name, area = names.get(c["floor_id"], ("Deleted location", "")) if c else ("", "")
            rows.append({"id": p["id"], "stream": p["stream"], "created_at": p["created_at"],
                         "check": {"id": c["id"], "floor_id": c["floor_id"], "date": c["date"], "round": c["round"], "location": name, "area": area} if c else None})
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)

    @app.delete("/api/{workspace}/checks/{check_id}/photos/{photo_id}")
    def delete_check_photo(workspace: Workspace, check_id: str, photo_id: str, _=Depends(authenticated)):
        """Remove a wrong photo from a check. The check and its ratings stay as they are."""
        check = store.get(f"{workspace}:checks", check_id)
        if not check or photo_id not in check["photos"]:
            raise HTTPException(404, "That photo is not attached to this check.")
        store.put(f"{workspace}:checks", check_id, {**check, "photos": [p for p in check["photos"] if p != photo_id], "updated_at": now()})
        photo_delete(workspace, photo_id)
        audit(workspace, "photo_deleted", check_id)
        return {"ok": True}

    @app.post("/api/{workspace}/cards/{floor_id}")
    def generate_card(workspace: Workspace, floor_id: str, payload: CardRequest, _=Depends(authenticated)):
        if payload.end > today():
            raise HTTPException(422, "Choose today or an earlier date.")
        result = make_card(store, workspace, floor_id, payload.end)
        audit(workspace, "card_generated", floor_id)
        return result

    @app.get("/api/{workspace}/cards")
    def cards(workspace: Workspace, _=Depends(authenticated)):
        return [c for c in store.list("cards") if c["workspace"] == workspace]

    @app.delete("/api/{workspace}/cards/{token}")
    def revoke(workspace: Workspace, token: str, _=Depends(authenticated)):
        value = store.get("cards", digest(token))
        if not value or value["workspace"] != workspace:
            raise HTTPException(404, "Card not found.")
        store.delete("cards", digest(token))
        store.delete("card-index", value["index"])
        return {"ok": True}

    @app.get("/api/public/cards/{token}")
    def public_card(token: str):
        if len(token) > 100:
            raise HTTPException(404, "Card not found.")
        value = store.get("cards", digest(token))
        if not value:
            raise HTTPException(404, "This scorecard link is invalid or has been revoked.")
        return {k: v for k, v in value.items() if k not in ("token", "index", "id")}

    # Worker link: a secret, revocable URL for sanitation staff. No operator code, no reading needed.
    def revoke_worker_link(workspace):
        current = store.get("worker-index", workspace)
        if current:
            store.delete("worker-links", digest(current["token"]))
            store.delete("worker-index", workspace)

    def worker_workspace(token):
        link = store.get("worker-links", digest(token)) if 0 < len(token) <= 100 else None
        if not link:
            raise HTTPException(404, "This worker link is invalid or has been turned off.")
        return link["workspace"]

    @app.get("/api/{workspace}/worker-link")
    def get_worker_link(workspace: Workspace, _=Depends(operator)):
        current = store.get("worker-index", workspace)
        return {"token": current["token"] if current else None}

    @app.post("/api/{workspace}/worker-link", status_code=201)
    def create_worker_link(workspace: Workspace, _=Depends(authenticated)):
        revoke_worker_link(workspace)
        token = secrets.token_urlsafe(24)
        store.put("worker-links", digest(token), {"workspace": workspace, "created_at": now()})
        store.put("worker-index", workspace, {"token": token})
        audit(workspace, "worker_link_created", "worker-link")
        return {"token": token}

    @app.delete("/api/{workspace}/worker-link")
    def delete_worker_link(workspace: Workspace, _=Depends(authenticated)):
        revoke_worker_link(workspace)
        audit(workspace, "worker_link_revoked", "worker-link")
        return {"ok": True}

    @app.get("/api/worker/{token}")
    def worker_view(token: str):
        workspace = worker_workspace(token)
        floors = sorted(store.list(f"{workspace}:floors"), key=location_order)
        return {"demo": workspace == "demo", "today": today().isoformat(),
                "floors": [{"id": f["id"], "name": f["name"], "area": f.get("area", "")} for f in floors]}

    @app.post("/api/worker/{token}/reports", status_code=201)
    def worker_report(token: str, payload: WorkerReport):
        workspace = worker_workspace(token)
        recent = attempts["worker:" + digest(token)]
        while recent and recent[0] < time.monotonic() - 3600:
            recent.popleft()
        if len(recent) >= 120:
            raise HTTPException(429, "Too many reports from this link. Try again in an hour.")
        recent.append(time.monotonic())
        if not store.get(f"{workspace}:floors", payload.floor_id):
            raise HTTPException(404, "Choose an existing floor.")
        day = today().isoformat()
        cid = f"{day}:{payload.floor_id}:collection"
        previous = store.get(f"{workspace}:checks", cid)
        value = {"id": cid, "floor_id": payload.floor_id, "date": day, "round": "collection",
                 "bio": payload.bio, "nonbio": payload.nonbio, "sanitary": payload.sanitary, "special": payload.special,
                 "deep": payload.deep, "kept_separate": None, "hazard": payload.hazard,
                 "issues": payload.issues,
                 "note": "", "photos": [], "human_confirmed": True, "reporter": "worker",
                 "created_at": previous["created_at"] if previous else now(), "updated_at": now(),
                 "source": "simulated" if workspace == "demo" else "real pilot"}
        # A second tap the same day replaces the first: the worker is correcting a mistake.
        value["evidence_version"] = str(uuid4())
        store.put(f"{workspace}:checks", cid, value)
        if previous:
            invalidate_cards(workspace)
        audit(workspace, "worker_report_corrected" if previous else "worker_report", cid)
        return {"ok": True, "replaced": bool(previous)}

    # My Bin Guide: public and stateless. The receipt teaches the household; it is never stored or scored.
    @app.post("/api/guide")
    def guide(payload: GuideRequest, request: Request):
        ip = request.client.host if request.client else "unknown"
        recent = attempts["guide:" + ip]
        while recent and recent[0] < time.monotonic() - 3600:
            recent.popleft()
        if len(recent) >= 30:
            raise HTTPException(429, "Too many receipts from here. Try again in an hour.")
        if not payload.text.strip() and not payload.image:
            raise HTTPException(422, "Paste the receipt text or add a receipt photo.")
        recent.append(time.monotonic())
        names, ai_parts, ai = items_from_text(payload.text), {}, "not_used"
        if payload.image:
            try:
                raw = sanitize(base64.b64decode(payload.image, validate=True))
            except (ValueError, TypeError) as exc:
                raise HTTPException(422, str(exc)) from exc
            ai, read, ai_parts = read_receipt(raw)
            names += [n for n in read if n.lower() not in {x.lower() for x in names}]
        return {**build_guide(names[:40], ai_parts), "ai": ai}

    @app.get("/api/{workspace}/export.csv")
    def export(workspace: Workspace, end: date | None = None, _=Depends(authenticated)):
        end = end or today()
        start = end - timedelta(days=6)
        floors = {f["id"]: f["name"] for f in store.list(f"{workspace}:floors")}
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["source", "floor", "date", "round", "bio", "nonbio", "kept_separate", "note", "created_at", "hazard", "reporter", "issues", "sanitary", "special", "deep_check"])
        def safe(value):
            text = str(value)
            return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text
        for check in store.list(f"{workspace}:checks"):
            if start.isoformat() <= check["date"] <= end.isoformat():
                values = [check["source"], floors.get(check["floor_id"], "Deleted floor"), check["date"], check["round"], check["bio"], check["nonbio"], {True: "yes", False: "no", None: "not observed"}[check["kept_separate"]], check["note"], check["created_at"], {True: "yes", False: "no", None: "not asked"}[check.get("hazard")], check.get("reporter", "operator"), ";".join(check.get("issues", [])), check.get("sanitary") or "no bin", check.get("special") or "no bin", "yes" if check.get("deep") else "no"]
                writer.writerow([safe(v) for v in values])
        return Response("\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="lane-{workspace}-{end.isoformat()}.csv"'})

    @app.get("/api/{workspace}/report.html")
    def weekly_report(workspace: Workspace, end: date | None = None, lang: Literal["en", "hi"] = "en", _=Depends(authenticated)):
        end = end or today()
        floors = store.list(f"{workspace}:floors")
        checks = store.list(f"{workspace}:checks")
        summary = summarize(floors, checks, end)
        previous = summarize(floors, checks, end - timedelta(days=7))
        content = render_report(summary, weekly_actions(summary, checks, previous), workspace, lang, community_goal(floors, checks, end))
        return HTMLResponse(content, headers={"Content-Disposition": f'attachment; filename="lane-{workspace}-{end.isoformat()}-report.html"'})

    @app.get("/api/{workspace}/audit")
    def audit_log(workspace: Workspace, _=Depends(operator)):
        return sorted(store.list(f"{workspace}:audit"), key=lambda x: x["at"], reverse=True)[:100]

    register_followups(app, store, authenticated, audit)

    app.mount("/assets", StaticFiles(directory=ROOT / "web"), name="assets")

    @app.get("/")
    @app.get("/card/{token}")
    def index():
        return FileResponse(ROOT / "web" / "index.html")

    @app.get("/guide")
    def guide_page():
        return FileResponse(ROOT / "web" / "guide.html")

    @app.get("/w/{token}")
    def worker_page(token: str):
        return FileResponse(ROOT / "web" / "worker.html")

    return app
