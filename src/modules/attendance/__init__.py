"""Attendance module package.

Avoid eager imports to prevent circular dependencies.
"""

from . import events  # Register SQLAlchemy event listeners.
from .models import *
from .routes import *