from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class APIErrorHandler:
    """Класс для обработки ошибок API."""
    
    @staticmethod
    def handle_result(result: BaseModel) -> JSONResponse:
        """Обработка результата операции."""
        result = result.model_dump(mode="json")
        if result.get("status") != 200:
            error_detail = "; ".join(result.get("errors")) if isinstance(result.get("errors"), list) else result.get("errors")
            raise HTTPException(status_code=result.get("status"), detail=error_detail)
        elif result.get("status") == 200:
            result.pop("status", None)
            result.pop("errors", None)
        return JSONResponse(content=result)
