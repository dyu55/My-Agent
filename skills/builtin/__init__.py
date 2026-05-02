"""Built-in skills for MyAgent."""

from .test_generation import TestGenerationSkill
from .api_design import ApiDesignSkill
from .doc_generation import DocGenerationSkill
from .browser_skill import BrowserSkill

__all__ = [
    "TestGenerationSkill",
    "ApiDesignSkill",
    "DocGenerationSkill",
    "BrowserSkill",
]