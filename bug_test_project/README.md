# Task Manager API

Flask REST API for task management with SQLite backend.

## Setup

```bash
pip install flask flask-cors
python app.py
```

## API Endpoints

- `GET /api/tasks` - List all tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/<id>` - Get single task
- `PUT /api/tasks/<id>` - Update task
- `DELETE /api/tasks/<id>` - Delete task