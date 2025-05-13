# Boomerang - Task Processing API

Boomerang is a FastAPI-based asynchronous task processing system with a web UI and API. It supports user authentication, task submission, and result retrieval, and is designed for easy extension with custom task processors.

## Features
- **User authentication** (HTTP Basic, with hashed passwords)
- **Task submission** via web form or API
- **Task status and result retrieval** (HTML and JSON)
- **Extensible task processor system** (add your own Python modules in `tasks/`)
- **Admin user auto-creation** on first run
- **SQLite database** with SQLAlchemy ORM

## Project Structure
```
boomerang/
├── app/
│   ├── api.py            # FastAPI endpoints
│   ├── database.py       # SQLAlchemy models and DB setup
│   ├── task_manager.py   # Task processor loading and execution
│   └── ...
├── tasks/                # Custom task processor modules
├── templates/            # Jinja2 HTML templates
├── main.py               # App entry point
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── ...
```

## Setup
1. **Clone the repository**
2. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```
3. **Configure environment variables**:
   - Copy `.env.template` to `.env` and set `APP_USERNAME`, `APP_PASSWORD`, etc.
4. **Run the app**:
   ```sh
   python main.py
   ```
   The app will be available at `http://localhost:8000` (or your configured port).

## Usage
- **Web UI**: Visit `/` to submit tasks and view results.
- **API**:
  - `POST /submit` — Submit a new task (form data: `task_type`, `input_text`)
  - `GET /task?id=...` — Get task status/result (HTML or JSON)
  - `GET /tasks` — List all tasks (JSON)
  - `GET /tasks/view` — List all tasks (HTML)
  - `GET /result?id=...` — Get raw result (plain text)

## Adding Custom Tasks
1. Add a new Python file in the `tasks/` directory.
2. Define a function and decorate it with `@task_processor`.
3. The function should accept a single argument (`input_text`) and return a result.

Example:
```python
from app.task_manager import task_processor

@task_processor
def my_task(input_text):
    return input_text[::-1]  # Reverse the input
```

## Security Notes
- Admin credentials are stored in the database with a hashed password.
- Protect your `.env` file and never commit secrets to version control.

## License
MIT
