"""
Common types used across API client modules.

This module contains type definitions used by multiple API client modules.
"""

from typing import TypedDict


class AuthTokenResponse(TypedDict):
    """Response from the auth/token endpoint"""

    token: str
    project_id: str


class UploadedObjectResponse(TypedDict):
    """Response from the v1/objects/upload endpoint"""

    url: str
    size: int
