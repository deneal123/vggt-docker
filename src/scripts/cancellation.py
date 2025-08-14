import os
import signal
import asyncio
import threading
from enum import Enum, auto
from typing import Dict, Any, Callable, Coroutine, Optional
from functools import wraps
from concurrent.futures import Future, ThreadPoolExecutor

from src.utils.custom_logging import get_logger

logger = get_logger(__name__)

class SessionType(Enum):
    """Перечисление типов сессий для их классификации."""
    BACKGROUND_TASK = auto()
    WEBSOCKET = auto()

class CancellationHandler:
    """Обрабатывает сигналы завершения для корректной остановки."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.cancelled = threading.Event()
        return cls._instance

    def cancel(self):
        if not self.cancelled.is_set():
            logger.warning("Получен сигнал отмены. Инициируется завершение работы...")
            self.cancelled.set()

    def check_cancellation(self):
        if self.cancelled.is_set():
            raise asyncio.CancelledError("Операция отменена пользователем.")

class SessionManager:
    """Управляет жизненным циклом активных сессий."""
    _sessions: Dict[Any, Dict[str, Any]] = {}
    _session_tasks: Dict[Any, asyncio.Task] = {}
    _executor = ThreadPoolExecutor(max_workers=os.cpu_count() or 1)
    _lock = threading.Lock()

    @classmethod
    def start_session(cls, session_id: Any, session_type: SessionType, name: str, ref: Any = None) -> None:
        """Запускает новую сессию с опциональной ссылкой на объект (например, WebSocket)"""
        with cls._lock:
            session_data = {
                "type": session_type, 
                "name": name
            }
            if ref is not None:
                session_data["ref"] = ref
            
            cls._sessions[session_id] = session_data
            logger.info(f"Сессия {session_id} ({name}) типа {session_type.name} запущена.")

    @classmethod
    def add_session(cls, session_id: Any, session_type: SessionType, ref: Any = None, name: str = "Unnamed") -> None:
        """Альтернативный метод для добавления сессии (для обратной совместимости)"""
        cls.start_session(session_id, session_type, name, ref)

    @classmethod
    async def shutdown_session(cls, session_id: Any) -> bool:
        """Корректно завершает сессию"""
        with cls._lock:
            session_exists = session_id in cls._sessions
            
            # Отменяем задачу если она существует
            if session_id in cls._session_tasks:
                task = cls._session_tasks.pop(session_id)
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=1.0)  # Сокращенный таймаут
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                    except Exception as e:
                        logger.error(f"Ошибка при отмене задачи сессии {session_id}: {e}")
            
            # Удаляем сессию
            if session_exists:
                cls._sessions.pop(session_id, None)
                logger.info(f"Сессия {session_id} была успешно завершена.")
                return True
        
        logger.warning(f"Попытка отменить несуществующую сессию {session_id}.")
        return False

    @classmethod
    def get_active_sessions(cls) -> Dict[Any, Dict[str, Any]]:
        with cls._lock:
            return dict(cls._sessions)

    @classmethod
    def add_task(cls, session_id: Any, task: asyncio.Task):
        """Добавляет задачу к сессии для возможности отмены"""
        with cls._lock:
            cls._session_tasks[session_id] = task

    @classmethod
    def remove_session(cls, session_id: Any):
        with cls._lock:
            cls._sessions.pop(session_id, None)
            cls._session_tasks.pop(session_id, None)
            logger.info(f"Сессия {session_id} завершена и удалена.")

    @classmethod
    def get_session(cls, session_id: Any) -> Optional[Dict[str, Any]]:
        """Получает информацию о сессии"""
        with cls._lock:
            return cls._sessions.get(session_id)

    @classmethod
    def shutdown_executor(cls):
        """Корректно завершает ThreadPoolExecutor"""
        if cls._executor:
            cls._executor.shutdown(wait=False, cancel_futures=True)  # Не ждем завершения
            logger.info("ThreadPoolExecutor завершен.")

class SessionManagerMixin:
    """Миксин для добавления управления сессиями к эндпоинтам FastAPI."""
    _session_counter = 0
    _lock = threading.Lock()

    @staticmethod
    def with_session_management(session_type: SessionType, name: str = "Unnamed"):
        def decorator(func: Callable[..., Coroutine]):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                with SessionManagerMixin._lock:
                    SessionManagerMixin._session_counter += 1
                    session_id = SessionManagerMixin._session_counter
                
                SessionManager.start_session(session_id, session_type, name)
                
                # Получаем текущую задачу и добавляем её к сессии
                current_task = asyncio.current_task()
                if current_task:
                    SessionManager.add_task(session_id, current_task)
                
                try:
                    return await func(*args, **kwargs)
                finally:
                    SessionManager.remove_session(session_id)
            return wrapper
        return decorator