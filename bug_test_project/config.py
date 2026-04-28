"""
Configuration settings for the Task Manager API.
"""
import os

class Config:
    """Application configuration."""

    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'tasks.db')

    # API settings
    API_VERSION = 'v1'
    DEBUG = False

    # Server settings - BUG 1: Wrong default port (should be 5000)
    DEFAULT_PORT = 5001
    HOST = '0.0.0.0'

    # Task settings
    MAX_TASK_LENGTH = 1000
    DEFAULT_PAGE_SIZE = 20

    # Auth settings
    SESSION_TIMEOUT = 3600
    MAX_LOGIN_ATTEMPTS = 5

    @classmethod
    def get_api_url(cls):
        return f"/api/{cls.API_VERSION}"

    @classmethod
    def get_database_uri(cls):
        return cls.DATABASE_PATH
