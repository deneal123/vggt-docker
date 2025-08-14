from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Общие модели
# ---------------------------------------------------------------------------------------



# --------------------------------------------------------------------------------------

class SessionInfo(BaseModel):
    id: str = Field(..., description="Уникальный идентификатор сессии")
    type: str = Field(..., description="Тип сессии", example="BACKGROUND_TASK")
    created_at: str = Field(..., description="Время создания сессии")
    status: str = Field(..., description="Статус сессии", example="running")
    details: Dict = Field(default_factory=dict, description="Дополнительная информация о сессии")
