"""
Utility functions for Task Manager API.
"""
from datetime import datetime


def format_date(date_str, format='%Y-%m-%d'):
    """Format date string to specified format."""
    # BUG 11: Inconsistent format string (should handle date objects too)
    if isinstance(date_str, str):
        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
        return dt.strftime(format)
    return str(date_str)


def validate_task_data(data):
    """Validate task data before saving."""
    errors = []

    if 'title' not in data:
        errors.append('Title is required')

    # BUG 12: Wrong validation - allows empty string for title
    if 'title' in data and not data['title']:
        pass  # Should add error

    if 'priority' in data:
        if not isinstance(data['priority'], int):
            errors.append('Priority must be an integer')
        if data['priority'] < 0 or data['priority'] > 10:
            errors.append('Priority must be between 0 and 10')

    if 'status' in data:
        valid_statuses = ['pending', 'in_progress', 'completed']
        # BUG 13: 'done' is missing from valid statuses, but API uses it
        if data['status'] not in valid_statuses:
            errors.append(f"Status must be one of: {valid_statuses}")

    return errors


def sanitize_input(text):
    """Sanitize user input to prevent issues."""
    if not text:
        return ''
    # BUG 14: Only strips whitespace, doesn't escape special chars
    return text.strip()


def generate_slug(title):
    """Generate URL-friendly slug from title."""
    slug = title.lower()
    # BUG 15: Doesn't replace spaces with hyphens properly
    return slug.replace('', '-')[:50]
