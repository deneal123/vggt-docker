import cv2
import os
import argparse
from tqdm import tqdm

def extract_frames_from_videos(input_dir, output_dir, step):
    # Поддерживаемые форматы видео
    supported_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.webm')
    
    # Проверка существования входной директории
    if not os.path.isdir(input_dir):
        raise NotADirectoryError(f"Директория с видео не найдена: {input_dir}")
    
    # Создание выходной директории
    os.makedirs(output_dir, exist_ok=True)
    
    # Поиск видеофайлов в директории
    video_files = [f for f in os.listdir(input_dir) 
                  if f.lower().endswith(supported_extensions)]
    
    if not video_files:
        raise FileNotFoundError(f"Видеофайлы не найдены в директории: {input_dir}")
    
    print(f"Найдено видеофайлов: {len(video_files)}")
    print(f"Шаг извлечения кадров: {step}")
    
    total_saved = 0
    
    for video_file in tqdm(video_files, desc="Обработка видео"):
        video_path = os.path.join(input_dir, video_file)
        video_name = os.path.splitext(video_file)[0]
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"⚠️ Ошибка открытия видео: {video_file}, пропускаем...")
            continue
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        saved_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % step == 0:
                frame_name = f"{video_name}_frame_{saved_count:06d}.jpg"
                output_path = os.path.join(output_dir, frame_name)
                cv2.imwrite(output_path, frame)
                saved_count += 1
                
            frame_count += 1
            
        cap.release()
        total_saved += saved_count
        print(f"├─ {video_file}: извлечено {saved_count}/{total_frames} кадров")
    
    print(f"└─ Всего сохранено кадров: {total_saved}")
    print(f"Кадры сохранены в: {os.path.abspath(output_dir)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Извлечение кадров из всех видео в директории')
    parser.add_argument('--input_dir', '-i', required=True, 
                        help='Путь к директории с видеофайлами')
    parser.add_argument('--output_dir', '-o', required=True, 
                        help='Директория для сохранения кадров')
    parser.add_argument('--step', '-s', type=int, default=30, 
                        help='Шаг извлечения кадров (по умолчанию: 30)')
    
    args = parser.parse_args()
    
    try:
        extract_frames_from_videos(args.input_dir, args.output_dir, args.step)
    except Exception as e:
        print(f"⛔ Ошибка: {str(e)}")
        exit(1)