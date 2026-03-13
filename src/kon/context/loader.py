"""
Context loader - loads and caches AGENTS.md files and skills.

This is loaded once at startup and passed to the agent for system prompt building.
The UI can also access it to display loaded resources.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agents import ContextFile, load_agents_files
from .skills import Skill, load_skills


@dataclass
class Context:
    cwd: str
    agents_files: list[ContextFile] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    skill_warnings: list[tuple[str, str]] = field(default_factory=list)

    @classmethod
    def load(cls, cwd: str) -> Context:
        agents_files = load_agents_files(cwd)
        skills_result = load_skills(cwd)

        return cls(
            cwd=cwd,
            agents_files=agents_files,
            skills=skills_result.skills,
            skill_warnings=[(w.path, w.message) for w in skills_result.warnings],
        )

    def reload(self) -> None:
        agents_files = load_agents_files(self.cwd)
        skills_result = load_skills(self.cwd)

        self.agents_files = agents_files
        self.skills = skills_result.skills
        self.skill_warnings = [(w.path, w.message) for w in skills_result.warnings]
