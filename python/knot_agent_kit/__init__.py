"""Small, dependency-free client for the Knot API."""

from .client import KnotApiError, KnotClient, create_registration_key

__all__ = ["KnotApiError", "KnotClient", "create_registration_key"]
__version__ = "0.1.0"
