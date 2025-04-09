from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import os
import uuid
import pandas as pd
from ultralytics import YOLO  # Или твой импорт, если он отличается

# ⚙️ Импорт твоей YOLO модели
model = YOLO("best.pt")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
CROPPED_DIR = "cropped"
COMPRESSED_DIR = "compressed"
CSV_DIR = "csv_logs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CROPPED_DIR, exist_ok=True)
os.makedirs(COMPRESSED_DIR, exist_ok=True)
os.makedirs(CSV_DIR, exist_ok=True)

# 📉 Сжатие изображения
def resize_image(input_path: str, output_path: str, width: int = 300):
    with Image.open(input_path) as img:
        w_percent = (width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((width, h_size), Image.ANTIALIAS)
        img.save(output_path)

# 🧠 Предикт и обрезка объектов
def process_with_yolo(image_path: str, username: str, base_id: str):

    yolo_model = YOLO(model)  # ← если best.model — путь до весов
    results = yolo_model(image_path)[0]  # Получаем первый результат (первый кадр)
    boxes = results.boxes.xyxy.cpu().numpy().tolist()  # [[x1, y1, x2, y2], ...]
    confidences = results.boxes.conf.cpu().numpy().tolist()
    labels = results.boxes.cls.cpu().numpy().tolist()

    output_data = []

    with Image.open(image_path) as img:
        for i, (bbox, conf, cls_id) in enumerate(zip(boxes, confidences, labels)):
            x1, y1, x2, y2 = map(int, bbox)
            cropped = img.crop((x1, y1, x2, y2))

            # Сохраняем кроп
            crop_id = f"{base_id}_{i}"
            cropped_path = os.path.join(CROPPED_DIR, f"{crop_id}.jpg")
            cropped.save(cropped_path)

            # Сжатие
            compressed_path = os.path.join(COMPRESSED_DIR, f"{crop_id}_compressed.jpg")
            resize_image(cropped_path, compressed_path)

            # Запись в логи
            output_data.append({
                "label": int(cls_id),
                "confidence": float(conf),
                "cropped_image": cropped_path,
                "compressed_image": compressed_path
            })

    return output_data

@app.post("/upload/")
async def upload_image(file: UploadFile, username: str = Form(...)):
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[-1]
    raw_path = os.path.join(UPLOAD_DIR, f"{file_id}{ext}")
    csv_path = os.path.join(CSV_DIR, f"{username}.csv")

    # Сохраняем оригинал
    with open(raw_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # YOLO + кроп + сжатие
    try:
        detections = process_with_yolo(raw_path, username, file_id)
    except Exception as e:
        return JSONResponse({"error": f"Failed to process image: {str(e)}"}, status_code=500)

    # CSV лог
    df = pd.DataFrame(detections)
    if os.path.exists(csv_path):
        df.to_csv(csv_path, mode='a', index=False, header=False)
    else:
        df.to_csv(csv_path, index=False)

    return JSONResponse({
        "message": "Image uploaded and processed by YOLO.",
        "detections_count": len(detections),
        "results": detections
    })
