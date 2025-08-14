from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.models.pydantic_models import SessionInfo


class HealthCheckResponse(BaseModel):
    status: int = Field(
        ...,
        examples=[200],
        description="Статус работы сервиса"
    )
    message: Optional[str] = Field(
        ...,
        examples=["Server is running"],
        description="Сообщение о состоянии сервиса"
    )
    version: str = Field(
        ...,
        examples=["1.0.0"],
        description="Версия сервиса"
    )
    errors: Optional[List[str]] = Field(
        None,
        description="Список ошибок, если есть",
        examples=["Database connection failed", "Cache service unavailable"]
    )


class ActiveSessionsResponse(BaseModel):
    status: int = Field(
        ...,
        examples=[200],
        description="Результат запроса на получение активных сессий"
    )
    message: Optional[str] = Field(
        ...,
        examples=["Active sessions retrieved successfully"],
        description="Сообщение о результате запроса"
    )
    sessions: Dict[str, SessionInfo] = Field(
        ...,
        description="Словарь активных сессий",
        examples=[{
            "session_id_1": {
                "user_id": "user_123",
                "type": "chat",
                "created_at": "2023-10-01T12:00:00Z",
                "last_activity": "2023-10-01T12:05:00Z"
            },
            "session_id_2": {
                "user_id": "user_456",
                "type": "search",
                "created_at": "2023-10-01T12:10:00Z",
                "last_activity": "2023-10-01T12:15:00Z"
            }
        }]
    )
    total: int = Field(
        ...,
        description="Общее количество активных сессий",
        examples=[0]
    )
    errors: Optional[List[str]] = Field(
        None,
        description="Список ошибок, если есть",
        examples=["Database connection failed", "Cache service unavailable"]
    )


class CancelSessionResponse(BaseModel):
    status: int = Field(
        ...,
        description="Результат запроса на отмену сессии",
        examples=[200]
    )
    message: Optional[str] = Field(
        ...,
        description="Сообщение о результате запроса",
        examples=["Session cancellation requested successfully"]
    )
    errors: Optional[List[str]] = Field(
        None,
        description="Список ошибок, если есть",
        examples=["Session not found", "Session already cancelled"]
    )


class Img2ColmapResponse(BaseModel):
    status: int = Field(
        ...,
        examples=[200],
        description="Результат запроса на преобразование изображений в формат COLMAP"
    )
    message: Optional[str] = Field(
        ...,
        examples=["Images converted to COLMAP format successfully"],
        description="Сообщение о результате запроса"
    )
    colmap_project: str = Field(
        ...,
        examples=["localhost:8000/dataset.zip"],
        description="Пути к файлам COLMAP"
    )
    errors: Optional[List[str]] = Field(
        None,
        description="Список ошибок, если есть",
        examples=["Image processing failed", "COLMAP conversion error"]
    )
