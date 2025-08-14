from __future__ import annotations
import os
import tempfile
from typing import Optional, Union
from pathlib import Path
from fastapi import UploadFile
from src.utils.custom_logging import get_logger


logger = get_logger(__name__)


class FileManager:
    """Менеджер для работы с временными файлами."""
    
    def __init__(self, target_directory: Optional[str] = None):
        """
        Инициализация FileManager.
        
        Args:
            target_directory: Путь к директории для сохранения файлов.
                            Если None, будет использоваться временная директория.
        """
        self.target_directory = target_directory
        self._created_temp_dir = False
        
        if self.target_directory:
            # Создаем директорию если она не существует
            Path(self.target_directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Использование директории: {self.target_directory}")
        else:
            # Создаем временную директорию
            self.target_directory = tempfile.mkdtemp(prefix="filemanager_")
            self._created_temp_dir = True
            logger.info(f"Создана временная директория: {self.target_directory}")
    
    async def save_uploaded_file(self, file: UploadFile, custom_filename: Optional[str] = None) -> str:
        """
        Сохранение загруженного файла.
        
        Args:
            file: Загруженный файл
            custom_filename: Пользовательское имя файла (опционально)
            
        Returns:
            Полный путь к сохраненному файлу
        """
        if not self.target_directory:
            raise ValueError("Target directory not set")
            
        # Определяем имя файла
        filename = custom_filename or file.filename or f"uploaded_file_{id(file)}"
        
        # Обеспечиваем безопасность имени файла
        filename = self._sanitize_filename(filename)
        
        file_path = os.path.join(self.target_directory, filename)
        
        # Если файл уже существует, добавляем суффикс
        file_path = self._get_unique_filepath(file_path)
        
        try:
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Файл сохранен: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла {filename}: {e}")
            raise
        finally:
            # Сбрасываем указатель файла для возможного повторного использования
            await file.seek(0)

    async def save_uploaded_files(self, files: list[UploadFile]) -> dict[str, Union[str, list[str]]]:
        """
        Сохранение нескольких загруженных файлов.
        
        Args:
            files: Список загруженных файлов
            
        Returns:
            Словарь с информацией о сохранении:
            {
                "directory": "путь к директории",
                "files": ["путь1", "путь2", ...],
                "count": количество_файлов
            }
        """
        if not files:
            raise ValueError("Список файлов пуст")
            
        file_paths = []
        
        for i, file in enumerate(files):
            try:
                file_path = await self.save_uploaded_file(file)
                file_paths.append(file_path)
            except Exception as e:
                logger.error(f"Ошибка при сохранении файла {i+1}/{len(files)}: {e}")
                # Очищаем уже сохраненные файлы при ошибке
                for saved_path in file_paths:
                    self.cleanup_file(saved_path)
                raise
        
        result = {
            "directory": self.target_directory,
            "files": file_paths,
            "count": len(file_paths)
        }
        
        logger.info(f"Сохранено {len(file_paths)} файлов в директорию: {self.target_directory}")
        return result
    
    def get_directory(self) -> str:
        """
        Получить путь к рабочей директории.
        
        Returns:
            Путь к директории где сохраняются файлы
        """
        return self.target_directory
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Удаление файла.
        
        Args:
            file_path: Путь к файлу для удаления
            
        Returns:
            True если файл успешно удален, False в противном случае
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Файл удален: {file_path}")
                return True
            else:
                logger.warning(f"Файл не найден для удаления: {file_path}")
                return False
        except Exception as e:
            logger.warning(f"Не удалось удалить файл {file_path}: {e}")
            return False
    
    def cleanup_directory(self, remove_directory: bool = False) -> bool:
        """
        Очистка рабочей директории.
        
        Args:
            remove_directory: Если True, удаляет саму директорию после очистки
                            (только для временных директорий)
            
        Returns:
            True если очистка прошла успешно
        """
        if not self.target_directory or not os.path.exists(self.target_directory):
            return True
            
        success = True
        
        try:
            # Удаляем все файлы в директории
            for filename in os.listdir(self.target_directory):
                file_path = os.path.join(self.target_directory, filename)
                if os.path.isfile(file_path):
                    if not self.cleanup_file(file_path):
                        success = False
            
            # Удаляем директорию если это временная директория и запрошено удаление
            if remove_directory and self._created_temp_dir:
                try:
                    os.rmdir(self.target_directory)
                    logger.info(f"Временная директория удалена: {self.target_directory}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временную директорию {self.target_directory}: {e}")
                    success = False
                    
        except Exception as e:
            logger.error(f"Ошибка при очистке директории {self.target_directory}: {e}")
            success = False
            
        return success
    
    def list_files(self, extension_filter: Optional[str] = None) -> list[str]:
        """
        Получить список файлов в рабочей директории.
        
        Args:
            extension_filter: Фильтр по расширению (например, '.jpg', '.png')
            
        Returns:
            Список путей к файлам
        """
        if not self.target_directory or not os.path.exists(self.target_directory):
            return []
            
        files = []
        try:
            for filename in os.listdir(self.target_directory):
                file_path = os.path.join(self.target_directory, filename)
                if os.path.isfile(file_path):
                    if extension_filter is None or filename.lower().endswith(extension_filter.lower()):
                        files.append(file_path)
        except Exception as e:
            logger.error(f"Ошибка при получении списка файлов: {e}")
            
        return files
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Очистка имени файла от небезопасных символов."""
        import re
        # Удаляем опасные символы
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Ограничиваем длину
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        return filename
    
    @staticmethod
    def _get_unique_filepath(file_path: str) -> str:
        """Получение уникального пути к файлу (добавление суффикса если файл существует)."""
        if not os.path.exists(file_path):
            return file_path
            
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_file_path = os.path.join(directory, new_filename)
            if not os.path.exists(new_file_path):
                return new_file_path
            counter += 1
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup_directory(remove_directory=self._created_temp_dir)


# # 1. Режим временной директории (как раньше)
# file_manager = FileManager()  # Создает временную директорию
# result = await file_manager.save_uploaded_files(files)
# print(f"Файлы сохранены в: {result['directory']}")

# # 2. Режим указанной директории
# file_manager = FileManager("/path/to/specific/directory")
# result = await file_manager.save_uploaded_files(files)
# print(f"Файлы сохранены в: {result['directory']}")

# # 3. С context manager (автоматическая очистка)
# with FileManager("/path/to/directory") as fm:
#     result = await fm.save_uploaded_files(files)
#     # Файлы автоматически очистятся при выходе из контекста (если это временная директория)

# # 4. Получение списка сохраненных файлов
# files_list = file_manager.list_files(extension_filter='.jpg')