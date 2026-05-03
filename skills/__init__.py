"""Skills module."""
from .registry import (
    BaseSkill,
    Skill,
    SkillContext,
    SkillRegistry,
    create_skill_registry,
    CodeReviewSkill,
    SecurityReviewSkill,
    InitSkill,
    SimplifySkill,
)

__all__ = [
    "Skill",
    "SkillContext",
    "SkillRegistry",
    "BaseSkill",
    "create_skill_registry",
    "CodeReviewSkill",
    "SecurityReviewSkill",
    "InitSkill",
    "SimplifySkill",
]

# Try to import builtin skills
try:
    from .builtin import TestGenerationSkill, ApiDesignSkill, DocGenerationSkill
    __all__.extend(["TestGenerationSkill", "ApiDesignSkill", "DocGenerationSkill"])
except ImportError:
    pass
