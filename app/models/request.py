from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    tool: str = Field(..., description="The name of the target tool (e.g., database, email, file)")
    action: str = Field(..., description="The action to be performed (e.g., delete, send, read)")
    dry_run: Optional[bool] = Field(default=False, description="Flag for simulating execution without performing the actual action")

    def get_extra_fields(self) -> Dict[str, Any]:
        """Utility to retrieve any dynamic fields passed in the request."""
        exclude_keys = {"tool", "action", "dry_run"}
        return {k: v for k, v in self.__dict__.items() if k not in exclude_keys}
