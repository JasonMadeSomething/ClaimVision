from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class APIResponse(BaseModel):
    status: str
    code: int
    message: str
    data: Optional[Union[Dict[str, Any], List[Any]]] = None
    error_details: Optional[str] = None

    def dict(self, **kwargs):
        """Overrides default dict() method to ensure correct serialization."""
        return super().model_dump(**kwargs, exclude_none=True)

    def json(self, **kwargs):
        """Overrides default json() method to ensure correct serialization."""
        return super().model_dump_json(**kwargs, exclude_none=True)
