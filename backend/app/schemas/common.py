"""
Common/shared schemas.
"""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters."""
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=100, ge=1, le=1000, description="Number of items to return")
    
    class Config:
        from_attributes = True
