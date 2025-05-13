import os
import importlib.util
import inspect
from datetime import datetime
from typing import Dict, Callable, Optional
from sqlalchemy.orm import Session
import logging

from app.database import SessionLocal, TaskCreateModel, TaskResponseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tasks")
os.makedirs(TASKS_DIR, exist_ok=True)

init_file = os.path.join(TASKS_DIR, "__init__.py")
if not os.path.exists(init_file):
    with open(init_file, "w") as f:
        pass

task_registry: Dict[str, Callable] = {}


def task_processor(func):
    func.is_task_processor = True
    return func


def load_task_processors():
    task_registry.clear()
    logger.info(f"Loading tasks from: {TASKS_DIR}")
    for filename in os.listdir(TASKS_DIR):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name = filename[:-3]
            module_path = os.path.join(TASKS_DIR, filename)

            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for name, obj in inspect.getmembers(module):
                        if inspect.isfunction(obj) and hasattr(
                            obj, "is_task_processor"
                        ):
                            task_registry[module_name] = obj
                            logger.info(
                                f"  Loaded task processor: {module_name} "
                                f"from {filename}"
                            )
                else:
                    logger.warning(f"Could not load spec for module: {module_name}")
            except Exception as e:
                logger.error(f"Error loading module {module_name} from {filename}: {e}")
    if not task_registry:
        logger.warning("No task processors found or loaded.")


async def process_task(task_id: str, input_text: str, task_type: str):
    db: Session = SessionLocal()
    try:
        task_create = (
            db.query(TaskCreateModel).filter(TaskCreateModel.id == task_id).first()
        )
        if task_create and task_create.response:
            task_response = task_create.response
            task_response.status = "processing"
            task_response.updated_at = datetime.now()
            db.commit()

            processor = task_registry.get(task_type)
            if not processor:
                task_response.status = "failed"
                task_response.result = f"Task type '{task_type}' not found"
                task_response.updated_at = datetime.now()
                logger.error(f"Processor for task type '{task_type}' not found.")
                db.commit()
                return

            try:
                logger.info(f"Executing task {task_id} with processor {task_type}")
                result_value = await processor(input_text)
                task_response.status = "completed"
                task_response.result = str(result_value)
                task_response.completed_at = datetime.now()
                task_response.updated_at = datetime.now()
                logger.info(f"Task {task_id} completed successfully.")
            except Exception as e:
                task_response.status = "failed"
                task_response.result = f"Error during execution: {str(e)}"
                task_response.updated_at = datetime.now()
                logger.error(f"Task {task_id} failed during execution: {e}")

            db.commit()
        else:
            logger.error(f"Task {task_id} not found during processing.")
            return

    except Exception as e:
        logger.error(f"Error in process_task function for task {task_id}: {e}")
        db.rollback()
        try:
            task_response = (
                db.query(TaskResponseModel)
                .join(TaskCreateModel)
                .filter(TaskCreateModel.id == task_id)
                .first()
            )
            if task_response:
                task_response.status = "failed"
                task_response.result = f"System error during processing: {str(e)}"
                task_response.updated_at = datetime.now()
                db.commit()
            else:
                logger.error(f"Task {task_id} not found for error update.")
        except Exception:
            pass
    finally:
        db.close()


def get_task_types():
    return list(task_registry.keys())
