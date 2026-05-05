"""Pydantic schemas for the AI Assistant Builder Mode."""

from typing import List, Optional

from pydantic import BaseModel, Field


class PlanTaskSchema(BaseModel):
    """Schema for a single task in a project plan."""

    id: str = Field(..., description="Unique identifier for the task")
    description: str = Field(..., description="Task description")
    estimatedMinutes: int = Field(
        ..., description="Estimated time to complete in minutes", ge=15, le=480
    )
    completed: bool = Field(default=False, description="Whether the task is completed")
    dependencies: Optional[List[str]] = Field(
        default=None, description="IDs of tasks that must complete before this one"
    )


class ProjectPlanSchema(BaseModel):
    """Schema for a complete project plan."""

    id: str = Field(..., description="Unique identifier for the plan")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    targetTrack: str = Field(..., description="Target hackathon track")
    estimatedHours: int = Field(
        ..., description="Estimated total hours to complete", ge=1, le=48
    )
    techStack: List[str] = Field(..., description="Recommended technologies")
    tasks: List[PlanTaskSchema] = Field(..., description="List of tasks to complete")
    stretchGoals: Optional[List[str]] = Field(
        default=None, description="Optional stretch goals"
    )


class GeneratedFileSchema(BaseModel):
    """Schema for a generated project file."""

    path: str = Field(..., description="File path relative to project root")
    name: str = Field(..., description="File name")
    content: str = Field(..., description="File content")
    language: str = Field(..., description="Programming language or file type")


class GenerateProjectRequest(BaseModel):
    """Request schema for project generation."""

    plan: ProjectPlanSchema = Field(..., description="The project plan to generate code for")
    projectType: str = Field(
        ...,
        description="Type of project to generate (e.g., 'react', 'python', 'fullstack')",
    )


class GenerateProjectResponse(BaseModel):
    """Response schema for project generation."""

    files: List[GeneratedFileSchema] = Field(
        ..., description="Generated project files"
    )
    readme: str = Field(..., description="Generated README content")
