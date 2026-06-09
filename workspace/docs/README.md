# TODO App Documentation

## Installation
```bash
cd /Users/donglingyu/Documents/MyAgent/workspace
pip install -r requirements.txt
```

## Usage
### CLI Mode
```bash
python app.py add "Buy groceries"
python app.py list
python app.py complete 1
python app.py delete 1
```

### Web Interface
```bash
python app.py --host 0.0.0.0 --port 5000
```

## API Reference

### Endpoints

#### GET /api/todos
- **Description**: List all todos
- **Response**: 
```json
[
  {"id": 1, "title": "Buy groceries", "completed": false, "created_at": "2023-01-01T10:00:00Z"}
]
```

#### POST /api/todos
- **Description**: Add new todo
- **Request Body**: 
```json
{"title": "Learn Python", "description": "Master Python basics"}
```
- **Response**: 
```json
{"id": 2, "title": "Learn Python", "completed": false, "created_at": "2023-01-01T11:00:00Z"}
```

#### PUT /api/todos/<id>
- **Description**: Update todo
- **Request Body**: 
```json
{"title": "Learn Python", "description": "Advanced Python concepts"}
```

#### DELETE /api/todos/<id>
- **Description**: Delete todo

## Data Storage
- SQLite database: `todos.db` in project root
- Schema: `id INTEGER PRIMARY KEY, title TEXT, description TEXT, completed BOOLEAN, created_at TIMESTAMP`

## License
MIT