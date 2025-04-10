from PIL import Image
import os
from ultralytics import YOLO

CROPPED_DIR = "cropped"
COMPRESSED_DIR = "compressed"

os.makedirs(CROPPED_DIR, exist_ok=True)
os.makedirs(COMPRESSED_DIR, exist_ok=True)

model = YOLO("best.pt")

def resize_image(input_path: str, output_path: str, width: int = 300):
    with Image.open(input_path) as img:
        w_percent = (width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((width, h_size), Image.ANTIALIAS)
        img.save(output_path)

def process_with_yolo(image_path: str, username: str, base_id: str):
    yolo_model = YOLO(model)
    results = yolo_model(image_path)[0]
    boxes = results.boxes.xyxy.cpu().numpy().tolist()
    confidences = results.boxes.conf.cpu().numpy().tolist()
    labels = results.boxes.cls.cpu().numpy().tolist()

    output_data = []

    with Image.open(image_path) as img:
        for i, (bbox, conf, cls_id) in enumerate(zip(boxes, confidences, labels)):
            x1, y1, x2, y2 = map(int, bbox)
            cropped = img.crop((x1, y1, x2, y2))
            crop_id = f"{base_id}_{i}"
            cropped_path = os.path.join(CROPPED_DIR, f"{crop_id}.jpg")
            cropped.save(cropped_path)
            compressed_path = os.path.join(COMPRESSED_DIR, f"{crop_id}_compressed.jpg")
            resize_image(cropped_path, compressed_path)
            output_data.append({
                "label": int(cls_id),
                "confidence": float(conf),
                "cropped_image": cropped_path,
                "compressed_image": compressed_path
            })

    return output_data
