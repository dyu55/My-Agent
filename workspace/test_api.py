"""Flask REST API Tests with JWT Authentication"""
import pytest
import json
from flask import Flask, request

# Create a test app instance for each test
@pytest.fixture
def client():
    """Create test client with fresh database"""
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
    from werkzeug.security import generate_password_hash, check_password_hash
    import datetime

    # Create fresh app for testing
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['JWT_SECRET_KEY'] = 'test-secret-key'
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    test_db = SQLAlchemy(test_app)
    test_jwt = JWTManager(test_app)

    # Define models inline
    class User(test_db.Model):
        __tablename__ = 'users'
        id = test_db.Column(test_db.Integer, primary_key=True)
        username = test_db.Column(test_db.String(80), unique=True, nullable=False)
        email = test_db.Column(test_db.String(120), unique=True, nullable=True)
        password_hash = test_db.Column(test_db.String(256), nullable=False)
        created_at = test_db.Column(test_db.DateTime, default=datetime.datetime.utcnow)

        tasks = test_db.relationship('Task', backref='user', lazy='dynamic', cascade='all, delete-orphan')

        def set_password(self, password):
            self.password_hash = generate_password_hash(password)

        def check_password(self, password):
            return check_password_hash(self.password_hash, password)

        def to_dict(self):
            return {'id': self.id, 'username': self.username, 'email': self.email}

    class Task(test_db.Model):
        __tablename__ = 'tasks'
        id = test_db.Column(test_db.Integer, primary_key=True)
        title = test_db.Column(test_db.String(200), nullable=False)
        description = test_db.Column(test_db.Text, nullable=True)
        completed = test_db.Column(test_db.Boolean, default=False)
        user_id = test_db.Column(test_db.Integer, test_db.ForeignKey('users.id'), nullable=False)

        def to_dict(self):
            return {'id': self.id, 'title': self.title, 'description': self.description,
                    'completed': self.completed, 'user_id': self.user_id}

    # Routes
    @test_app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        if not data or 'username' not in data or 'password' not in data:
            return {'msg': 'Username and password are required'}, 400

        if User.query.filter_by(username=data['username']).first():
            return {'msg': 'Username already exists'}, 400

        user = User(username=data['username'], email=data.get('email'))
        user.set_password(data['password'])
        test_db.session.add(user)
        test_db.session.commit()

        token = create_access_token(identity=str(user.id))
        return {'msg': 'User created', 'access_token': token, 'user': user.to_dict()}, 201

    @test_app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        user = User.query.filter_by(username=data.get('username')).first()
        if not user or not user.check_password(data.get('password', '')):
            return {'msg': 'Invalid credentials'}, 401

        token = create_access_token(identity=str(user.id))
        return {'msg': 'Login successful', 'access_token': token}, 200

    @test_app.route('/tasks', methods=['GET'])
    @jwt_required()
    def get_tasks():
        user_id = int(get_jwt_identity())
        tasks = Task.query.filter_by(user_id=user_id).all()
        return [t.to_dict() for t in tasks], 200

    @test_app.route('/tasks', methods=['POST'])
    @jwt_required()
    def create_task():
        user_id = int(get_jwt_identity())
        data = request.get_json()
        if not data or 'title' not in data:
            return {'msg': 'Title is required'}, 400

        task = Task(title=data['title'], description=data.get('description', ''),
                    completed=data.get('completed', False), user_id=user_id)
        test_db.session.add(task)
        test_db.session.commit()
        return task.to_dict(), 201

    @test_app.route('/tasks/<int:task_id>', methods=['GET'])
    @jwt_required()
    def get_task(task_id):
        user_id = int(get_jwt_identity())
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return {'msg': 'Not found'}, 404
        return task.to_dict(), 200

    @test_app.route('/tasks/<int:task_id>', methods=['PUT'])
    @jwt_required()
    def update_task(task_id):
        user_id = int(get_jwt_identity())
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return {'msg': 'Not found'}, 404

        data = request.get_json()
        if 'title' in data:
            task.title = data['title']
        if 'completed' in data:
            task.completed = data['completed']
        test_db.session.commit()
        return task.to_dict(), 200

    @test_app.route('/tasks/<int:task_id>', methods=['DELETE'])
    @jwt_required()
    def delete_task(task_id):
        user_id = int(get_jwt_identity())
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return {'msg': 'Not found'}, 404
        test_db.session.delete(task)
        test_db.session.commit()
        return {'msg': 'Deleted', 'result': True}, 200

    with test_app.app_context():
        test_db.create_all()
        yield test_app.test_client()
        test_db.drop_all()


# Helper functions
def register_user(client, username, password):
    resp = client.post('/register',
        data=json.dumps({'username': username, 'password': password}),
        content_type='application/json')
    return resp

def get_token(client, username, password):
    resp = register_user(client, username, password)
    if resp.status_code == 201:
        return json.loads(resp.data)['access_token']
    return None


# Tests
def test_register_success(client):
    resp = register_user(client, 'testuser', 'testpass123')
    assert resp.status_code == 201
    data = json.loads(resp.data)
    assert 'access_token' in data

def test_register_duplicate_username(client):
    register_user(client, 'testuser', 'testpass123')
    resp = register_user(client, 'testuser', 'anotherpass')
    assert resp.status_code == 400

def test_register_missing_fields(client):
    resp = client.post('/register',
        data=json.dumps({'username': 'testuser'}),
        content_type='application/json')
    assert resp.status_code == 400

def test_login_success(client):
    register_user(client, 'testuser', 'testpass123')
    resp = client.post('/login',
        data=json.dumps({'username': 'testuser', 'password': 'testpass123'}),
        content_type='application/json')
    assert resp.status_code == 200
    assert 'access_token' in json.loads(resp.data)

def test_login_invalid_credentials(client):
    register_user(client, 'testuser', 'testpass123')
    resp = client.post('/login',
        data=json.dumps({'username': 'testuser', 'password': 'wrongpass'}),
        content_type='application/json')
    assert resp.status_code == 401

def test_login_nonexistent_user(client):
    resp = client.post('/login',
        data=json.dumps({'username': 'nonexistent', 'password': 'pass'}),
        content_type='application/json')
    assert resp.status_code == 401

def test_jwt_protected_endpoint_without_token(client):
    resp = client.get('/tasks')
    assert resp.status_code == 401

def test_jwt_protected_endpoint_with_invalid_token(client):
    resp = client.get('/tasks', headers={'Authorization': 'Bearer invalid'})
    assert resp.status_code == 422

def test_create_task(client):
    token = get_token(client, 'testuser', 'pass123')
    resp = client.post('/tasks',
        data=json.dumps({'title': 'Test Task', 'description': 'A test'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 201
    assert json.loads(resp.data)['title'] == 'Test Task'

def test_get_tasks(client):
    token = get_token(client, 'testuser', 'pass123')
    client.post('/tasks',
        data=json.dumps({'title': 'Task 1'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    resp = client.get('/tasks', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert len(json.loads(resp.data)) == 1

def test_get_task_by_id(client):
    token = get_token(client, 'testuser', 'pass123')
    create_resp = client.post('/tasks',
        data=json.dumps({'title': 'Test Task'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    task_id = json.loads(create_resp.data)['id']
    resp = client.get(f'/tasks/{task_id}', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['title'] == 'Test Task'

def test_get_task_not_found(client):
    token = get_token(client, 'testuser', 'pass123')
    resp = client.get('/tasks/9999', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404

def test_update_task(client):
    token = get_token(client, 'testuser', 'pass123')
    create_resp = client.post('/tasks',
        data=json.dumps({'title': 'Original'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    task_id = json.loads(create_resp.data)['id']
    resp = client.put(f'/tasks/{task_id}',
        data=json.dumps({'title': 'Updated'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200
    assert json.loads(resp.data)['title'] == 'Updated'

def test_update_task_not_found(client):
    token = get_token(client, 'testuser', 'pass123')
    resp = client.put('/tasks/9999',
        data=json.dumps({'title': 'Updated'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404

def test_delete_task(client):
    token = get_token(client, 'testuser', 'pass123')
    create_resp = client.post('/tasks',
        data=json.dumps({'title': 'Delete Me'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    task_id = json.loads(create_resp.data)['id']
    resp = client.delete(f'/tasks/{task_id}', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200

def test_delete_task_not_found(client):
    token = get_token(client, 'testuser', 'pass123')
    resp = client.delete('/tasks/9999', headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 404

def test_create_task_unauthorized(client):
    resp = client.post('/tasks',
        data=json.dumps({'title': 'Test'}),
        content_type='application/json')
    assert resp.status_code == 401

def test_create_task_missing_title(client):
    token = get_token(client, 'testuser', 'pass123')
    resp = client.post('/tasks',
        data=json.dumps({'description': 'No title'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 400

def test_task_isolation_between_users(client):
    """Different users should not see each other's tasks"""
    token1 = get_token(client, 'user1', 'pass1')
    token2 = get_token(client, 'user2', 'pass2')

    client.post('/tasks',
        data=json.dumps({'title': 'User1 Task'}),
        content_type='application/json',
        headers={'Authorization': f'Bearer {token1}'})

    resp = client.get('/tasks', headers={'Authorization': f'Bearer {token2}'})
    assert resp.status_code == 200
    assert len(json.loads(resp.data)) == 0


if __name__ == '__main__':
    pytest.main(['-v', __file__])