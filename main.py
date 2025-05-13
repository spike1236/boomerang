import os
import uvicorn
import dotenv
from app.database import init_db
from app.api import app

dotenv.load_dotenv()

APP_HOST = os.environ.get("APP_HOST", "0.0.0.0")
APP_PORT = int(os.environ.get("APP_PORT", "8000"))

if __name__ == "__main__":
    init_db()
    uvicorn.run("app.api:app", host=APP_HOST, port=APP_PORT, reload=True)
