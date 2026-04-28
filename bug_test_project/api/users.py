"""
User API endpoints.
"""
from flask import Blueprint, request, jsonify
from database import get_db_cursor

users_bp = Blueprint('users', __name__)


@users_bp.route('/users', methods=['GET'])
def get_users():
    """Get all users."""
    with get_db_cursor() as cursor:
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
    return jsonify([dict(u) for u in users])


@users_bp.route('/users', methods=['POST'])
def create_user():
    """Create new user."""
    data = request.get_json()
    if not data or 'username' not in data:
        return jsonify({'error': 'Username is required'}), 400

    with get_db_cursor() as cursor:
        # BUG 8: No validation for duplicate username
        cursor.execute('''
            INSERT INTO users (username, email)
            VALUES (?, ?)
        ''', (data['username'], data.get('email', '')))
        user_id = cursor.lastrowid

        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()

    return jsonify(dict(user)), 201


@users_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID."""
    with get_db_cursor() as cursor:
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()

    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(dict(user))