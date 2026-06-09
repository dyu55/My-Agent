from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['JWT_SECRET_KEY'] = 'jwt-secret-key-change-in-production'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=24)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'todo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# --- Models ---

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    tasks = db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=0)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'completed': self.completed,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# --- Create tables ---
with app.app_context():
    db.create_all()


# --- API Routes ---

@app.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'msg': 'Username and password are required'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip() or None

    if not username or not password:
        return jsonify({'msg': 'Username and password cannot be empty'}), 400

    if len(password) < 6:
        return jsonify({'msg': 'Password must be at least 6 characters'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'msg': 'Username already exists'}), 400

    user = User(username=username, email=email)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'msg': 'User created successfully',
        'access_token': access_token,
        'user': user.to_dict()
    }), 201


@app.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'msg': 'Username and password are required'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'msg': 'Invalid username or password'}), 401

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'msg': 'Login successful',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200


@app.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    """Get all tasks for the authenticated user"""
    user_id = int(get_jwt_identity())
    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.created_at.desc()).all()
    return jsonify([task.to_dict() for task in tasks]), 200


@app.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    """Create a new task"""
    user_id = int(get_jwt_identity())
    data = request.get_json()

    if not data or 'title' not in data:
        return jsonify({'msg': 'Title is required'}), 400

    title = data.get('title', '').strip()
    if not title:
        return jsonify({'msg': 'Title cannot be empty'}), 400

    task = Task(
        title=title,
        description=data.get('description', ''),
        completed=data.get('completed', False),
        priority=data.get('priority', 0),
        due_date=datetime.datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        user_id=user_id
    )

    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


@app.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """Get a specific task"""
    user_id = int(get_jwt_identity())
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()

    if not task:
        return jsonify({'msg': 'Task not found'}), 404

    return jsonify(task.to_dict()), 200


@app.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """Update a task"""
    user_id = int(get_jwt_identity())
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()

    if not task:
        return jsonify({'msg': 'Task not found'}), 404

    data = request.get_json()

    if 'title' in data:
        title = data.get('title', '').strip()
        if not title:
            return jsonify({'msg': 'Title cannot be empty'}), 400
        task.title = title

    if 'description' in data:
        task.description = data.get('description', '')

    if 'completed' in data:
        task.completed = bool(data.get('completed'))

    if 'priority' in data:
        task.priority = int(data.get('priority', 0))

    if 'due_date' in data:
        task.due_date = datetime.datetime.fromisoformat(data['due_date']) if data.get('due_date') else None

    db.session.commit()

    return jsonify(task.to_dict()), 200


@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """Delete a task"""
    user_id = int(get_jwt_identity())
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()

    if not task:
        return jsonify({'msg': 'Task not found'}), 404

    db.session.delete(task)
    db.session.commit()

    return jsonify({'msg': 'Task deleted successfully', 'result': True}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({'msg': 'Resource not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)