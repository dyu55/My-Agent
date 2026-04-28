"""
Task API endpoints.
"""
from flask import Blueprint, request, jsonify
from models import Task

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks."""
    limit = request.args.get('limit', 50, type=int)
    tasks = Task.get_all(limit=limit)
    # BUG 6: Task.get_all() returns empty list due to bug in models/task.py
    # Also: Should pass list of dicts, not Task objects
    return jsonify([task.to_dict() for task in tasks])


@tasks_bp.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get single task by ID."""
    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    return jsonify(task.to_dict())


@tasks_bp.route('/tasks', methods=['POST'])
def create_task():
    """Create new task."""
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400

    task = Task.create(
        title=data['title'],
        description=data.get('description', ''),
        priority=data.get('priority', 0)
    )
    return jsonify(task.to_dict()), 201


@tasks_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update existing task."""
    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    data = request.get_json()
    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = data['status']
    if 'priority' in data:
        task.priority = data['priority']

    task.save()
    return jsonify(task.to_dict())


@tasks_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete task."""
    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    task.delete()
    return jsonify({'message': 'Task deleted successfully'}), 200


@tasks_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Mark task as completed."""
    task = Task.get_by_id(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    # BUG 7: Should be 'completed' not 'done'
    task.status = 'done'
    task.save()
    return jsonify(task.to_dict())
