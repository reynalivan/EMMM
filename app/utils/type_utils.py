# app/utils/type_utils.py
from typing import Type, TypeVar, Optional
import logging

T = TypeVar("T")

logger = logging.getLogger(__name__)


def ensure_model_type(model: object, expected_type: Type[T]) -> Optional[T]:
    """Safely ensures a model is of the expected type."""
    if isinstance(model, expected_type):
        return model
    else:
        logger.error(
            f"Model type mismatch: Expected {expected_type.__name__}, got {type(model).__name__}."
        )
        return None
