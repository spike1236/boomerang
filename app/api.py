import os
from contextlib import asynccontextmanager
from fastapi import (
    FastAPI,
    BackgroundTasks,
    Form,
    HTTPException,
    Depends,
    Request,
    Query,
)
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from datetime import datetime
from sqlalchemy.orm import Session
import dotenv
import hashlib
import secrets

from app.database import (
    get_db,
    AccountModel,
    TaskCreateModel,
    TaskResponseModel,
    SessionLocal,
)
from app.task_manager import load_task_processors, process_task, get_task_types


dotenv.load_dotenv()

APP_PASSWORD = os.environ.get("APP_PASSWORD")
APP_USERNAME = os.environ.get("APP_USERNAME")

security = HTTPBasic()


def hash_password(password: str) -> str:
    """Hash a password for storing."""
    salt = secrets.token_hex(8)
    pwdhash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    )
    return f"{salt}${pwdhash.hex()}"


def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a stored password against one provided by user"""
    if not stored_password or not provided_password:
        return False

    try:
        salt, stored_hash = stored_password.split("$")
        pwdhash = hashlib.pbkdf2_hmac(
            "sha256", provided_password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return pwdhash.hex() == stored_hash
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_task_processors()
    yield


app = FastAPI(title="Task Processing API", lifespan=lifespan)

templates_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=templates_path)


def authorize(credentials: HTTPBasicCredentials = Depends(security)):
    db = SessionLocal()
    try:
        admin = (
            db.query(AccountModel)
            .filter(AccountModel.username == credentials.username)
            .first()
        )
        if not admin or not verify_password(admin.password_hash, credentials.password):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Basic"},
            )
        return True
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    _: bool = Depends(authorize),
):
    task_types = get_task_types()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "task_types": task_types,
        },
    )


@app.post("/submit")
async def submit_task(
    task_type: str = Form(...),
    input_text: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    if task_type not in get_task_types():
        raise HTTPException(
            status_code=404, detail=f"Task type '{task_type}' not found"
        )

    task_create = TaskCreateModel(
        input_text=input_text,
        task_type=task_type,
        created_at=datetime.now(),
    )
    db.add(task_create)
    db.commit()
    db.refresh(task_create)

    task_response = TaskResponseModel(
        task_id=task_create.id,
        status="pending",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(task_response)
    db.commit()

    background_tasks.add_task(process_task, task_create.id, input_text, task_type)

    return {"task_id": task_create.id, "message": "Task submitted successfully"}


@app.get("/task", response_class=HTMLResponse)
async def get_task(
    request: Request,
    id: int,
    format: str = Query("html", enum=["html", "json"]),
    db: Session = Depends(get_db),
    _: bool = Depends(authorize),
):
    task_create = db.query(TaskCreateModel).filter(TaskCreateModel.id == id).first()
    if not task_create or not task_create.response:
        raise HTTPException(status_code=404, detail="Task not found")
    task_response = task_create.response
    task_type = task_create.task_type

    if format == "json":
        return JSONResponse(
            content={
                "id": id,
                "input_text": task_create.input_text,
                "status": task_response.status,
                "result": task_response.result,
                "created_at": (
                    task_create.created_at.isoformat()
                    if task_create.created_at
                    else None
                ),
                "updated_at": (
                    task_response.updated_at.isoformat()
                    if task_response.updated_at
                    else None
                ),
                "completed_at": (
                    task_response.completed_at.isoformat()
                    if task_response.completed_at
                    else None
                ),
                "task_type": task_type,
            }
        )
    else:
        raw_result_content = ""
        if task_response.result and task_response.status == "completed":
            raw_result_content = task_response.result
        elif task_response.status == "failed":
            raw_result_content = f"Error:\n```\n{task_response.result}\n```"
        elif task_response.status == "processing":
            raw_result_content = "Task is still processing..."
        elif task_response.status == "pending":
            raw_result_content = "Task is pending execution..."
        else:
            raw_result_content = "No result available yet."

        task_data = {
            "id": id,
            "input_text": task_create.input_text,
            "status": task_response.status,
            "result": task_response.result,
            "created_at": task_create.created_at,
            "updated_at": task_response.updated_at,
            "completed_at": task_response.completed_at,
            "task_type": task_type,
        }

        return templates.TemplateResponse(
            "task_detail.html",
            {
                "request": request,
                "task": task_data,
                "raw_result_content": raw_result_content,
            },
        )


@app.get("/tasks", response_class=JSONResponse)
async def list_tasks(db: Session = Depends(get_db), _: bool = Depends(authorize)):
    task_creates = (
        db.query(TaskCreateModel).order_by(TaskCreateModel.created_at.desc()).all()
    )

    tasks_data = []
    for task_create in task_creates:
        status = "pending"
        created_at = task_create.created_at

        if task_create.response:
            status = task_create.response.status

        tasks_data.append(
            {
                "id": task_create.id,
                "status": status,
                "created_at": created_at.isoformat() if created_at else None,
                "task_type": task_create.task_type,
            }
        )

    return {"tasks": tasks_data}


@app.get("/tasks/view", response_class=HTMLResponse)
async def view_tasks(
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(authorize),
):
    task_creates = (
        db.query(TaskCreateModel).order_by(TaskCreateModel.created_at.desc()).all()
    )

    tasks_data = []
    for task_create in task_creates:
        task_data = {
            "id": task_create.id,
            "task_type": task_create.task_type,
            "created_at": task_create.created_at,
            "status": "pending",
        }

        if task_create.response:
            task_data["status"] = task_create.response.status

        tasks_data.append(task_data)

    return templates.TemplateResponse(
        "tasks.html", {"request": request, "tasks": tasks_data}
    )


@app.get("/result", response_class=PlainTextResponse)
async def get_result(
    id: int = Query(..., description="Task ID"),
    db: Session = Depends(get_db),
    _: bool = Depends(authorize),
):
    task_response = (
        db.query(TaskResponseModel)
        .join(TaskCreateModel)
        .filter(TaskCreateModel.id == id)
        .first()
    )
    if not task_response:
        raise HTTPException(status_code=404, detail="Task not found")
    raw = task_response.result or ""
    return raw
