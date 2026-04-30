import os, fitz, io
from PIL import Image
import cv2
import numpy as np
import torch
from transformers import ViTImageProcessor, ViTForImageClassification

vit_model_path = "vit-base-letters_2"
vit_input_format = "google/vit-base-patch16-224"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

vit_feature_extractor = ViTImageProcessor.from_pretrained(vit_input_format)
new_model = ViTForImageClassification.from_pretrained(vit_model_path).to(device)
new_model.eval()

def predict_letter(img: Image.Image) -> str:
    inputs = vit_feature_extractor(img.convert("RGB"), return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = new_model(**inputs)
    pred_id = outputs.logits.argmax(-1).item()
    id2label = {int(k): v for k, v in new_model.config.id2label.items()}
    return id2label.get(pred_id, '?')

CROPS = {
    "surnames": lambda img: img.crop((0, 0, img.width, img.height // 3)),
    "names": lambda img: img.crop((0, img.height // 3, img.width, 2 * img.height // 3)),
    "codewords": lambda img: img.crop((0, 2 * img.height // 3, img.width - 540, img.height)),
}

def split_word_image_into_letters(image):
    gray = image.convert("L")
    img_np = np.array(gray)
    binary = cv2.adaptiveThreshold(img_np, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 15, 12)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if w < 2 or h < 5 or area < 10 or w < 25 or h < 25 or w > 120 or h > 120:
            continue
        boxes.append((x, y, x + w, y + h))

    boxes = sorted(boxes, key=lambda b: b[0])
    return [image.crop(box) for box in boxes]

def extract_blue_text(input_path: str) -> Image.Image:
    image, y = prepare_cropped_image(input_path)
    if y == 0:
        raise ValueError(f"Невозможно обрезать PDF по границе: {input_path}")

    crop = image.crop((
        int(image.width * 0.025),
        int(image.height * 0.07),
        int(image.width * 0.67),
        int(image.height * 0.215)
    ))

    hsv = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, np.array([75, 30, 30]), np.array([140, 255, 255]))

    if cv2.countNonZero(mask) / (mask.shape[0] * mask.shape[1]) < 0.005:
        raise ValueError(f"Синий текст не найден или слишком слабый: {input_path}")

    mask = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)
    result = np.zeros_like(np.array(crop))
    result[mask > 0] = [255, 255, 255]
    return Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY))

def prepare_cropped_image(pdf_path: str):
    doc = fitz.open(pdf_path)
    img = Image.open(io.BytesIO(doc[0].get_pixmap(dpi=300).tobytes("png")))
    img = img.crop((30, 30, img.width - 30, img.height - 30))

    def find_first_content_row(im):
        gray = im.convert("L")
        px = np.array(gray)
        for y in range(px.shape[0]):
            if np.mean(px[y]) < 250:
                return y
        return 0

    y = find_first_content_row(img)
    return img.crop((0, y, img.width, img.height)), y

def process_single_pdf(pdf_path: str) -> dict:
    try:
        image = extract_blue_text(pdf_path)
    except Exception as e:
        print(f"Ошибка: {e}")
        return {}

    words = {}
    for category, crop_fn in CROPS.items():
        letters = split_word_image_into_letters(crop_fn(image))
        text = ''.join(predict_letter(img) for img in letters)
        words[category] = text

    print(f"\nРаспознанные данные ({os.path.basename(pdf_path)}):")
    print("Фамилия:  ", words.get("surnames", "—"))
    print("Имя:      ", words.get("names", "—"))
    print("Кодовое:  ", words.get("codewords", "—"))

    return words
