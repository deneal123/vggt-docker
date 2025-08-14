import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import signal
import sys
import threading

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    HTTPException,
    File,
    UploadFile,
    Form,
    Query,
    Body,
    Path,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import Tag as OpenApiTag
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import zipfile

from src import path_to_project

# --- Логи/утилиты ---
from src.utils.custom_logging import get_logger
from src.utils.api_error_handler import APIErrorHandler
from src.utils.file_manager import FileManager

# --- Сессии/отмена ---
from src.scripts.cancellation import (
    CancellationHandler,
    SessionType,
    SessionManager,
    SessionManagerMixin,
)

# --- Модели ---
# from src.models.request_models import (
    # Img2ColmapRequest,
# )
from src.models.response_models import (
    HealthCheckResponse,
    ActiveSessionsResponse,
    CancelSessionResponse,
    Img2ColmapResponse,
)

load_dotenv()
logger = get_logger(__name__)

# Глобальная переменная для управления завершением
shutdown_event = asyncio.Event()
force_shutdown = False

def force_exit():
    """Принудительное завершение приложения"""
    global force_shutdown
    if force_shutdown:
        logger.critical("Принудительное завершение приложения...")
        os._exit(1)
    else:
        force_shutdown = True
        logger.warning("Следующий Ctrl+C приведет к принудительному завершению...")

# ------------------------------------------------------------------------------
# Жизненный цикл приложения
# ------------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    cancellation = CancellationHandler()
    
    # Счетчик нажатий Ctrl+C
    shutdown_count = 0
    
    def signal_handler():
        nonlocal shutdown_count
        shutdown_count += 1
        
        if shutdown_count == 1:
            logger.info("Получен сигнал завершения, инициируется остановка...")
            shutdown_event.set()
            cancellation.cancel()
            
            # Запланировать завершение через некоторое время
            def delayed_shutdown():
                import time
                time.sleep(2)  # Даем 2 секунды на нормальное завершение
                if not shutdown_event.is_set():
                    logger.warning("Нормальное завершение не удалось, принудительное завершение...")
                    os._exit(1)
            
            # Запускаем отложенное завершение в отдельном потоке
            threading.Thread(target=delayed_shutdown, daemon=True).start()
            
        elif shutdown_count >= 2:
            logger.critical("Получен повторный сигнал, принудительное завершение...")
            os._exit(1)
    
    # Устанавливаем обработчики сигналов
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    logger.info("Приложение запущено...")

    try:
        yield
    finally:
        logger.info("Начало остановки приложения...")
        
        # Отменяем все активные сессии
        active_sessions = SessionManager.get_active_sessions()
        if active_sessions:
            logger.info(f"Закрытие {len(active_sessions)} активных сессий...")
            shutdown_tasks = []
            for sid in list(active_sessions):
                task = asyncio.create_task(SessionManager.shutdown_session(sid))
                shutdown_tasks.append(task)
            
            # Ждем завершения всех задач с таймаутом
            try:
                await asyncio.wait_for(
                    asyncio.gather(*shutdown_tasks, return_exceptions=True),
                    timeout=2.0  # Сокращаем таймаут до 2 секунд
                )
            except asyncio.TimeoutError:
                logger.warning("Таймаут при закрытии сессий")
        
        # Завершаем ThreadPoolExecutor
        SessionManager.shutdown_executor()
        logger.info("Остановка завершена.")



# ------------------------------------------------------------------------------
# Приложения FastAPI
# ------------------------------------------------------------------------------

app = FastAPI(lifespan=lifespan)

app_server = FastAPI(
    title="VGGT Server API",
    version="0.1.0",
    description="API-сервер для VGGT модели.",
    contact={"name": "dfvolkhin@edu.hse.ru"},
    lifespan=lifespan,
)
app.mount("/server", app_server)

path_to_temp_dir = os.path.join(path_to_project(), "dataset")
path_to_images = os.path.join(path_to_temp_dir, "images")
path_to_colmap = os.path.join(path_to_temp_dir, "sparse/0")
path_colmap_project = os.path.join(path_to_project(), "colmap")

if not os.path.exists(path_to_temp_dir):
    os.makedirs(path_to_temp_dir)
if not os.path.exists(path_to_images):
    os.makedirs(path_to_images)
if not os.path.exists(path_to_colmap):
    os.makedirs(path_to_colmap)
if not os.path.exists(path_colmap_project):
    os.makedirs(path_colmap_project)

# Статические файлы
app_server.mount(
    "/colmap",
    StaticFiles(directory=os.path.join(path_to_project(), "colmap")),
    name="colmap"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Теги Swagger
app_server.openapi_tags = [
    OpenApiTag(name="Health", description="Проверка состояния сервера.").model_dump(),
    OpenApiTag(name="Session", description="Управление пользовательскими сессиями.").model_dump(),
    OpenApiTag(
        name="Main",
        description="Основные операции.",
    ).model_dump(),
]



# ------------------------------------------------------------------------------
# Системные эндпоинты
# ------------------------------------------------------------------------------

@app_server.get("/health", tags=["Health"], summary="Проверить работоспособность сервера")
async def health_check():
    if shutdown_event.is_set():
        raise HTTPException(status_code=503, detail="Server is shutting down")
    
    CancellationHandler().check_cancellation()
    return APIErrorHandler.handle_result(
        HealthCheckResponse(status=200, message="Server is running", version=app_server.version)
    )


@app_server.get("/api/sessions", tags=["Session"], summary="Получить список активных сессий")
async def get_active_sessions():
    if shutdown_event.is_set():
        raise HTTPException(status_code=503, detail="Server is shutting down")
        
    CancellationHandler().check_cancellation()
    sessions = SessionManager.get_active_sessions()
    for _, session_data in sessions.items():
        if isinstance(session_data.get("type"), SessionType):
            session_data["type"] = session_data["type"].name
    return APIErrorHandler.handle_result(
        ActiveSessionsResponse(
            status=status.HTTP_200_OK,
            message="Active sessions retrieved successfully.",
            sessions=sessions,
            total=len(sessions))
    )


@app_server.post("/api/cancel-session/{session_id}", tags=["Session"], summary="Отменить сессию по ID")
async def cancel_session(session_id: str = Path(..., description="ID сессии для отмены")):
    if shutdown_event.is_set():
        raise HTTPException(status_code=503, detail="Server is shutting down")
        
    CancellationHandler().check_cancellation()
    sid_to_cancel = int(session_id) if session_id.isdigit() else session_id
    if await SessionManager.shutdown_session(sid_to_cancel):
        return APIErrorHandler.handle_result(
            CancelSessionResponse(message=f"Session {session_id} cancelled successfully.")
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")


# ------------------------------------------------------------------------------
# Основные ручки
# ------------------------------------------------------------------------------


@SessionManagerMixin.with_session_management(SessionType.BACKGROUND_TASK, "img2colmap")
@app_server.post("/api/img2colmap", tags=["Main"], summary="VGGT image to COLMAP processing")
async def img2colmap(
    images: list[UploadFile] = File(
        ...,
        description="Список изображений для обработки",
        media_type="multipart/form-data",
        examples=[{
            "filename": "image1.jpg", "content_type": "image/jpeg"
        }]
    ),
    conf_threshold: Optional[float] = Form(
        0.2,
        description="Confidence threshold for filtering points.",
        ge=0.0, le=1.0,
        examples=[0.2]
    ),
    mask_sky: Optional[bool] = Form(
        False,
        description="Whether to mask the sky in the images.",
        examples=[False]
    ),
    mask_black_bg: Optional[bool] = Form(
        False,
        description="Whether to mask black backgrounds in the images.",
        examples=[False]
    ),
    mask_white_bg: Optional[bool] = Form(
        False,
        description="Whether to mask white backgrounds in the images.",
        examples=[False]
    ),
    stride: Optional[int] = Form(
        1,
        description="Stride for point sampling (higher = fewer points)",
        ge=1,
        examples=[1]
    )
):
    if shutdown_event.is_set():
        raise HTTPException(status_code=503, detail="Server is shutting down")
    
    CancellationHandler().check_cancellation()
    
    try:
        logger.info(f"Сохранение изображений во временную директорию: {path_to_images}")
        file_manager = FileManager(path_to_images)
        file_paths = await file_manager.save_uploaded_files(images)
        logger.info(f"Изображения успешно сохранены: {file_paths}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении изображений: {e}")
        return APIErrorHandler.handle_result(
            Img2ColmapResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Ошибка при сохранении изображений: " + str(e),
                path_to_colmap="",
                errors=[str(e)]
            )
        )

    command = [
        "uv", "run", "--project", path_to_project(), "--active", "python", "src/scripts/vggt_to_colmap.py",
        "--image_dir", path_to_images,
        "--output_dir", path_to_colmap,
        "--conf_threshold", str(conf_threshold),
        "--stride", str(stride),
        "--binary"
    ]

    if mask_sky:
        command.append("--mask_sky")
    if mask_black_bg:
        command.append("--mask_black_bg")
    if mask_white_bg:
        command.append("--mask_white_bg")
    
    env = {
        "PYTHONPATH": path_to_project(),
        "PATH": f"{path_to_project()}/bin:" + os.environ.get("PATH", "")
    }
    
    for key, value in os.environ.items():
        if key not in env:
            env[key] = value

    try:
        logger.info("Запуск обработки изображений с помощью vggt_to_colmap...")
        logger.info(f"Команда: {' '.join(command)}")
        logger.info(f"Рабочая директория: {os.getcwd()}")
        logger.info(f"PYTHONPATH: {env.get('PYTHONPATH', 'не установлен')}")
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=path_to_project()
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300.0
            )
            
            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""
            
            if stdout_text:
                logger.info(f"STDOUT из vggt_to_colmap:\n{stdout_text}")
            if stderr_text:
                logger.warning(f"STDERR из vggt_to_colmap:\n{stderr_text}")
            
            if process.returncode != 0:
                error_msg = f"Скрипт vggt_to_colmap завершился с кодом {process.returncode}"
                if stderr_text:
                    error_msg += f"\nОшибки:\n{stderr_text}"
                if stdout_text:
                    error_msg += f"\nВывод:\n{stdout_text}"
                
                logger.error(error_msg)
                raise subprocess.CalledProcessError(
                    process.returncode, 
                    "vggt_to_colmap", 
                    stderr_text
                )
                
        except asyncio.TimeoutError:
            logger.error("Таймаут при выполнении vggt_to_colmap")
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="Обработка изображений превысила максимальное время выполнения"
            )
            
        except asyncio.CancelledError:
            logger.info("Обработка изображений была отменена")
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            raise
        
        logger.info("Обработка изображений завершена успешно")
        
        expected_files = ["cameras.bin", "images.bin", "points3D.bin"]
        missing_files = []
        for file in expected_files:
            file_path = os.path.join(path_to_colmap, file)
            if not os.path.exists(file_path):
                missing_files.append(file)

        if missing_files:
            logger.warning(f"Отсутствуют ожидаемые выходные файлы: {missing_files}")

        zip_file_path = os.path.join(path_colmap_project, "dataset.zip")

        os.makedirs(path_colmap_project, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(path_to_temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, path_to_temp_dir)
                        zipf.write(file_path, arcname)
                        logger.debug(f"Добавлен в архив: {arcname}")
                    
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        arcname = os.path.relpath(dir_path, path_to_temp_dir) + "/"
                        if not os.listdir(dir_path):
                            zipf.writestr(arcname, "")
                            logger.debug(f"Добавлена пустая директория: {arcname}")
            
            zip_size = os.path.getsize(zip_file_path)
            logger.info(f"ZIP архив создан: {zip_file_path}, размер: {zip_size} байт")
            
            with zipfile.ZipFile(zip_file_path, 'r') as zipf:
                archive_contents = zipf.namelist()
                logger.info(f"Содержимое архива ({len(archive_contents)} элементов): {archive_contents[:10]}...")

        except Exception as e:
            logger.error(f"Ошибка при создании ZIP архива: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось создать архив: {str(e)}"
            )

        server_host = os.getenv("SERVER_HOST", "localhost")
        server_port = os.getenv("SERVER_PORT", "8000")
        download_url = f"http://{server_host}:{server_port}/server/colmap/dataset.zip"

        return APIErrorHandler.handle_result(
            Img2ColmapResponse(
                status=status.HTTP_200_OK,
                message="Изображения успешно обработаны и сохранены в COLMAP формате.",
                colmap_project=download_url,
            )
        )
    
    except asyncio.CancelledError:
        logger.info("Обработка изображений была отменена")
        raise HTTPException(status_code=499, detail="Request was cancelled")
    
    except subprocess.CalledProcessError as e:
        error_details = {
            "return_code": e.returncode,
            "command": ' '.join(command),
            "stderr": e.stderr if hasattr(e, 'stderr') and e.stderr else "Нет данных об ошибке",
            "stdout": e.stdout if hasattr(e, 'stdout') and e.stdout else "Нет вывода"
        }
        
        logger.error(f"Детали ошибки vggt_to_colmap: {error_details}")
        
        return APIErrorHandler.handle_result(
            Img2ColmapResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Ошибка при обработке изображений. Код возврата: {e.returncode}. "
                       f"Ошибка: {error_details['stderr']}",
                colmap_project="",
                errors=[
                    f"Return code: {e.returncode}",
                    f"Command: {error_details['command']}",
                    f"Error output: {error_details['stderr']}",
                    f"Standard output: {error_details['stdout']}"
                ]
            )
        )
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запуске vggt_to_colmap: {e}", exc_info=True)
        return APIErrorHandler.handle_result(
            Img2ColmapResponse(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Неожиданная ошибка: {str(e)}",
                colmap_project="",
                errors=[str(e)]
            )
        )
    finally:
        if os.path.exists(path_to_images):
            file_manager.cleanup_directory(path_to_images)
            logger.info(f"Временные файлы в {path_to_images} удалены")
        if os.path.exists(path_to_colmap):
            file_manager.cleanup_directory(path_to_colmap)
            logger.info(f"Временные файлы в {path_to_colmap} удалены")



# ------------------------------------------------------------------------------
# Точка входа (uvicorn)
# ------------------------------------------------------------------------------
def run_server():
    import logging.config
    import yaml
    from src import path_to_logging

    uvicorn_log_config_path = path_to_logging()
    with open(uvicorn_log_config_path, "r") as f:
        log_config = yaml.safe_load(f)

    logging.config.dictConfig(log_config)
    reload = os.getenv("DEBUG", "false").lower() == "true"

    def main_signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum} в основном процессе")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, main_signal_handler)
    signal.signal(signal.SIGTERM, main_signal_handler)

    import uvicorn
    
    try:
        uvicorn.run(
            "src.pipeline.server:app",
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8000")),
            log_config=log_config,
            reload=reload,
        )
    except KeyboardInterrupt:
        logger.info("Получен KeyboardInterrupt, завершение...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка при запуске сервера: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_server()