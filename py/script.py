import os
import fitz  # PyMuPDF
import shutil
from openpyxl import Workbook
from openpyxl.styles import Alignment
import time
from openpyxl.drawing.image import Image as XLImage
from PIL import Image
import io
import yadisk
from PyPDF2 import PdfReader, PdfWriter

# Авторизация
yandex = yadisk.YaDisk(token="y0__xDG74akqveAAhjblgMggf6o1xKS9mEBdAxviZ1aAoqtrPku2rA5qA")

def save_to_yandex_disk(save_folder, file_path):
    filename = os.path.basename(file_path)
    print(f"Начало Загрузки: {filename}")
    name, ext = os.path.splitext(filename)
    if not yandex.exists(save_folder):
        yandex.mkdir(save_folder)

    i = 1
    # Проверка и подбор имени
    while yandex.exists(f"{save_folder}/{filename}"):
        filename = f"{name} ({i}){ext}"
        i += 1

    yandex.upload(file_path, f"{save_folder}/{filename}")
    print(f"Загружено: {filename}")

def crop_image_by_pixels(pdf_path, crops):
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=75)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    parts = []
    for left,top,right, bottom in crops:
        cropped = image.crop((left, top, right, bottom))
        buf = io.BytesIO()
        cropped.save(buf, format='PNG')
        parts.append(buf)
    return parts

def split_pdf_by_pages(input_pdf_path, output_folder, chunk_size=2):
    print("📄 Режем PDF на части...")
    filename = os.path.splitext(os.path.basename(input_pdf_path))[0]
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)
    os.makedirs(output_folder, exist_ok=True)

    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        for j in range(i, min(i + chunk_size, total_pages)):
            writer.add_page(reader.pages[j])
        part_filename = os.path.join(output_folder, f"{filename}_{int(i/2)}.pdf")
        with open(part_filename, "wb") as f_out:
            writer.write(f_out)
        print(f"✅ Сохранён: {part_filename}")
    
    os.remove(input_pdf_path)

def insert_images_to_excel(pdf_folder, output_excel):
    wb = Workbook()
    ws = wb.active

    row = 1
    for filename in os.listdir(pdf_folder):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(pdf_folder, filename)

        save_to_yandex_disk("/output",pdf_path)
        print(f"Начало Обработки: {filename}")
        # Укажи здесь crop'ы по пикселям (top, bottom)
        crops = [
            (40, 90,300,200),      # верхняя часть
            (200,90,500 ,200),    # средняя часть # нижняя часть
        ]

        images = crop_image_by_pixels(pdf_path, crops)
        max_height_px = 0  # Для определения максимальной высоты строки

        col = 1
        cell = ws.cell(row=row, column=1, value=os.path.splitext(filename)[0])
        cell.alignment = Alignment(horizontal="center", vertical="center")

        for _, img_buf in enumerate(images, start=1):
            if img_buf:
                col += 1
                img = XLImage(img_buf)
                pil_img = Image.open(img_buf)
                width_px, height_px = pil_img.size

                cell = ws.cell(row=row, column=col)
                ws.add_image(img, cell.coordinate)

                ws.column_dimensions[cell.column_letter].width = width_px / 7

                if height_px > max_height_px:
                    max_height_px = height_px

        ws.row_dimensions[row].height = max_height_px * 0.75
        row += 1
        print(f"Конец Обработки: {filename}")

    wb.save(output_excel)
    save_to_yandex_disk("/xlsx", output_excel)
    os.remove(output_excel)


# === Шаги обработки ===
# 1. Скачиваем один PDF с Яндекс.Диска
REMOTE_PDF_PATH = "/input/34329.pdf"
LOCAL_PDF_PATH = "../pdfs/34329.pdf"
PDF_OUTPUT_FOLDER = "../pdfs"
EXCEL_OUTPUT_PATH = "out.xlsx"

start = time.time()
print("⬇️ Загружаем PDF с Яндекс.Диска...")

shutil.rmtree("../pdfs/", ignore_errors=True)
os.mkdir("../pdfs/")
yandex.download(REMOTE_PDF_PATH, LOCAL_PDF_PATH)

# 2. Режем по 2 страницы
split_pdf_by_pages(LOCAL_PDF_PATH, PDF_OUTPUT_FOLDER)

# 3. Обрабатываем порезанные PDF-файлы
insert_images_to_excel(PDF_OUTPUT_FOLDER, EXCEL_OUTPUT_PATH)

end = time.time()
print(f"⏱ Выполнено за {end - start:.2f} секунд")
