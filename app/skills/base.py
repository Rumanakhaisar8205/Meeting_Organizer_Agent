"""
Lab 3: Skill Creation Base Class
Provides a unified abstract interface for schema-typed, reusable skills.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseSkill(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for all agent skills.
    Skills package repeatable capability as reusable, schema-typed functions.
    """

    name: str
    description: str

    @abstractmethod
    def execute(self, inputs: InputT) -> OutputT:
        """Execute the skill with typed input schema and return typed output schema."""
        pass

    def __call__(self, inputs: InputT) -> OutputT:
        return self.execute(inputs)
