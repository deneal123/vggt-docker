#!/usr/bin/env python3
"""
Скрипт для разбивки широкой панорамы на тайлы фиксированного размера
с перекрытием минимум 20 процентов
"""

import os
import sys
from PIL import Image
import argparse
import math


def tile_panorama(input_path, output_dir, tile_width=1024, tile_height=1024, overlap_percent=20):
    """
    Разбивает панораму на тайлы с заданным перекрытием
    
    Args:
        input_path (str): Путь к входному изображению панорамы
        output_dir (str): Директория для сохранения тайлов
        tile_width (int): Ширина тайла в пикселях
        tile_height (int): Высота тайла в пикселях
        overlap_percent (int): Процент перекрытия (минимум 20)
    """
    
    # Проверяем минимальное перекрытие
    if overlap_percent < 20:
        overlap_percent = 20
        print(f"Предупреждение: перекрытие увеличено до минимума 20%")
    
    # Загружаем изображение
    try:
        image = Image.open(input_path)
        print(f"Загружена панорама: {image.size[0]}x{image.size[1]} пикселей")
    except Exception as e:
        print(f"Ошибка при загрузке изображения: {e}")
        return
    
    # Создаем выходную директорию
    os.makedirs(output_dir, exist_ok=True)
    
    # Вычисляем параметры тайлинга
    img_width, img_height = image.size
    
    # Вычисляем шаг с учетом перекрытия
    step_x = int(tile_width * (100 - overlap_percent) / 100)
    step_y = int(tile_height * (100 - overlap_percent) / 100)
    
    print(f"Размер тайла: {tile_width}x{tile_height}")
    print(f"Перекрытие: {overlap_percent}%")
    print(f"Шаг по X: {step_x}, шаг по Y: {step_y}")
    
    # Вычисляем количество тайлов
    tiles_x = math.ceil((img_width - tile_width) / step_x) + 1 if img_width > tile_width else 1
    tiles_y = math.ceil((img_height - tile_height) / step_y) + 1 if img_height > tile_height else 1
    
    print(f"Будет создано тайлов: {tiles_x} x {tiles_y} = {tiles_x * tiles_y}")
    
    tile_count = 0
    
    # Генерируем тайлы
    for row in range(tiles_y):
        for col in range(tiles_x):
            # Вычисляем координаты для текущего тайла
            x = col * step_x
            y = row * step_y
            
            # Корректируем координаты, чтобы не выйти за границы изображения
            if x + tile_width > img_width:
                x = img_width - tile_width
            if y + tile_height > img_height:
                y = img_height - tile_height
            
            # Убеждаемся, что координаты не отрицательные
            x = max(0, x)
            y = max(0, y)
            
            # Вырезаем тайл
            box = (x, y, x + tile_width, y + tile_height)
            tile = image.crop(box)
            
            # Формируем имя файла
            filename = f"tile_{row:03d}_{col:03d}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            # Сохраняем тайл
            tile.save(filepath, "JPEG", quality=95)
            tile_count += 1
            
            print(f"Сохранен тайл {tile_count}: {filename} (координаты: {x}, {y})")
    
    print(f"\nГотово! Создано {tile_count} тайлов в директории '{output_dir}'")


def main():
    parser = argparse.ArgumentParser(description="Разбивка панорамы на тайлы с перекрытием")
    
    parser.add_argument("input", help="Путь к входному файлу панорамы")
    parser.add_argument("-o", "--output", default="tiles", 
                       help="Директория для сохранения тайлов (по умолчанию: tiles)")
    parser.add_argument("-w", "--width", type=int, default=1024,
                       help="Ширина тайла в пикселях (по умолчанию: 1024)")
    parser.add_argument("--height", type=int, default=1024,
                       help="Высота тайла в пикселях (по умолчанию: 1024)")
    parser.add_argument("--overlap", type=int, default=20,
                       help="Процент перекрытия (минимум 20, по умолчанию: 20)")
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    if not os.path.exists(args.input):
        print(f"Ошибка: файл '{args.input}' не найден")
        sys.exit(1)
    
    # Запускаем тайлинг
    tile_panorama(
        input_path=args.input,
        output_dir=args.output,
        tile_width=args.width,
        tile_height=args.height,
        overlap_percent=args.overlap
    )


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
Скрипт для разбивки широкой панорамы на тайлы фиксированного размера
с перекрытием минимум 20 процентов
"""

import os
import sys
from PIL import Image
import argparse
import math


def tile_panorama(input_path, output_dir, tile_width=1024, tile_height=1024, overlap_percent=20):
    """
    Разбивает панораму на тайлы с заданным перекрытием
    
    Args:
        input_path (str): Путь к входному изображению панорамы
        output_dir (str): Директория для сохранения тайлов
        tile_width (int): Ширина тайла в пикселях
        tile_height (int): Высота тайла в пикселях
        overlap_percent (int): Процент перекрытия (минимум 20)
    """
    
    # Проверяем минимальное перекрытие
    if overlap_percent < 20:
        overlap_percent = 20
        print(f"Предупреждение: перекрытие увеличено до минимума 20%")
    
    # Загружаем изображение
    try:
        image = Image.open(input_path)
        print(f"Загружена панорама: {image.size[0]}x{image.size[1]} пикселей")
    except Exception as e:
        print(f"Ошибка при загрузке изображения: {e}")
        return
    
    # Создаем выходную директорию
    os.makedirs(output_dir, exist_ok=True)
    
    # Вычисляем параметры тайлинга
    img_width, img_height = image.size
    
    # Вычисляем шаг с учетом перекрытия
    step_x = int(tile_width * (100 - overlap_percent) / 100)
    step_y = int(tile_height * (100 - overlap_percent) / 100)
    
    print(f"Размер тайла: {tile_width}x{tile_height}")
    print(f"Перекрытие: {overlap_percent}%")
    print(f"Шаг по X: {step_x}, шаг по Y: {step_y}")
    
    # Вычисляем количество тайлов
    tiles_x = math.ceil((img_width - tile_width) / step_x) + 1 if img_width > tile_width else 1
    tiles_y = math.ceil((img_height - tile_height) / step_y) + 1 if img_height > tile_height else 1
    
    print(f"Будет создано тайлов: {tiles_x} x {tiles_y} = {tiles_x * tiles_y}")
    
    tile_count = 0
    
    # Генерируем тайлы
    for row in range(tiles_y):
        for col in range(tiles_x):
            # Вычисляем координаты для текущего тайла
            x = col * step_x
            y = row * step_y
            
            # Корректируем координаты, чтобы не выйти за границы изображения
            if x + tile_width > img_width:
                x = img_width - tile_width
            if y + tile_height > img_height:
                y = img_height - tile_height
            
            # Убеждаемся, что координаты не отрицательные
            x = max(0, x)
            y = max(0, y)
            
            # Вырезаем тайл
            box = (x, y, x + tile_width, y + tile_height)
            tile = image.crop(box)
            
            # Формируем имя файла
            filename = f"tile_{row:03d}_{col:03d}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            # Сохраняем тайл
            tile.save(filepath, "JPEG", quality=95)
            tile_count += 1
            
            print(f"Сохранен тайл {tile_count}: {filename} (координаты: {x}, {y})")
    
    print(f"\nГотово! Создано {tile_count} тайлов в директории '{output_dir}'")


def main():
    parser = argparse.ArgumentParser(description="Разбивка панорамы на тайлы с перекрытием")
    
    parser.add_argument("input", help="Путь к входному файлу панорамы")
    parser.add_argument("-o", "--output", default="tiles", 
                       help="Директория для сохранения тайлов (по умолчанию: tiles)")
    parser.add_argument("-w", "--width", type=int, default=1024,
                       help="Ширина тайла в пикселях (по умолчанию: 1024)")
    parser.add_argument("--height", type=int, default=1024,
                       help="Высота тайла в пикселях (по умолчанию: 1024)")
    parser.add_argument("--overlap", type=int, default=20,
                       help="Процент перекрытия (минимум 20, по умолчанию: 20)")
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    if not os.path.exists(args.input):
        print(f"Ошибка: файл '{args.input}' не найден")
        sys.exit(1)
    
    # Запускаем тайлинг
    tile_panorama(
        input_path=args.input,
        output_dir=args.output,
        tile_width=args.width,
        tile_height=args.height,
        overlap_percent=args.overlap
    )


if __name__ == "__main__":
    main()