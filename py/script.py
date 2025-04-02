import os
import fitz  # PyMuPDF
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image
import io
import yadisk
from PyPDF2 import PdfReader, PdfWriter

# Авторизация
yandex = yadisk.YaDisk(token="y0__xDG74akqveAAhjblgMggf6o1xKS9mEBdAxviZ1aAoqtrPku2rA5qA")

def save_to_yandex_disk(save_folder, file_path):
    filename = os.path.basename(file_path)
    if not yandex.exists(save_folder):
        yandex.mkdir(save_folder)

    yandex.upload(file_path, f"{save_folder}/{filename}")
    print(f"Загружено: {filename}")

def crop_image_by_pixels(pixmap, crops):
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    width, height = image.size
    parts = []
    for top, bottom in crops:
        cropped = image.crop((0, top, width, bottom))
        buf = io.BytesIO()
        cropped.save(buf, format='PNG')
        parts.append(buf)
    return parts

def process_pdf(pdf_path, crops):
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return [None, None, None]

    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    return crop_image_by_pixels(pix, crops)

def split_pdf_by_pages(input_pdf_path, output_folder, chunk_size=2):
    print("📄 Режем PDF на части...")
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)
    os.makedirs(output_folder, exist_ok=True)

    part_num = 1
    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        for j in range(i, min(i + chunk_size, total_pages)):
            writer.add_page(reader.pages[j])

        part_filename = os.path.join(output_folder, f"part_{part_num:03}.pdf")
        with open(part_filename, "wb") as f_out:
            writer.write(f_out)
        print(f"✅ Сохранён: {part_filename}")
        part_num += 1

def insert_images_to_excel(pdf_folder, output_excel):
    wb = Workbook()
    ws = wb.active

    row = 1
    for filename in os.listdir(pdf_folder):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(pdf_folder, filename)
        print(f"Обработка: {filename}")

        save_to_yandex_disk("/output",pdf_path)

        # Укажи здесь crop'ы по пикселям (top, bottom)
        crops = [
            (0, 400),      # верхняя часть
            (400, 800),    # средняя часть
            (800, 1200),   # нижняя часть
        ]

        images = process_pdf(pdf_path, crops)
        max_height_px = 0  # Для определения максимальной высоты строки

        col = 1
        ws.cell(row=row, column=1, value=os.path.splitext(filename)[0] + "_" + str(row))

        for _, img_buf in enumerate(images, start=1):
            if img_buf:
                col += 1
                img = XLImage(img_buf)
                pil_img = Image.open(img_buf)
                width_px, height_px = pil_img.size

                cell = ws.cell(row=row, column=col)
                ws.add_image(img, cell.coordinate)

                col_letter = cell.column_letter
                ws.column_dimensions[col_letter].width = width_px / 7

                if height_px > max_height_px:
                    max_height_px = height_px

        ws.row_dimensions[row].height = max_height_px * 0.75
        row += 1

    wb.save(output_excel)
    print(f"📊 Excel сохранён в: {output_excel}")

# === Шаги обработки ===
# 1. Скачиваем один PDF с Яндекс.Диска
REMOTE_PDF_PATH = "/input/merged.pdf"
LOCAL_PDF_PATH = "../pdfs/downloaded.pdf"
PDF_OUTPUT_FOLDER = "../pdfs"
EXCEL_OUTPUT_PATH = "out.xlsx"

print("⬇️ Загружаем PDF с Яндекс.Диска...")
os.makedirs("../pdfs/", exist_ok=True)
yandex.download(REMOTE_PDF_PATH, LOCAL_PDF_PATH)

# 2. Режем по 2 страницы
split_pdf_by_pages(LOCAL_PDF_PATH, PDF_OUTPUT_FOLDER)

# 3. Обрабатываем порезанные PDF-файлы
insert_images_to_excel(PDF_OUTPUT_FOLDER, EXCEL_OUTPUT_PATH)
