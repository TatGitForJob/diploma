import os
import fitz  # PyMuPDF
import shutil
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
import time
from openpyxl.drawing.image import Image as XLImage
from PIL import Image
import io
import yadisk
from PyPDF2 import PdfReader, PdfWriter
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()
loop = asyncio.get_event_loop()
upload_tasks = []
crops = [
    (25, 90,400,200),      # верхняя часть
    (410,90,600 ,200),    # средняя часть # нижняя часть
]
colums_width=[20,54,20,20,20,28,10,10,70]
pdfs_url="https://docs.yandex.ru/docs/view?url=ya-disk%3A%2F%2F%2Fdisk%2Foutput%2F34329_0%20(10).pdf&name=34329_0%20(10).pdf&uid=1130000065607622&nosw=1"

async def async_save_to_yandex_disk(save_folder, file_path):
    await loop.run_in_executor(executor, save_to_yandex_disk, save_folder, file_path)

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

def crop_image_by_pixels(pdf_path):
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

def prepare_excel(ws):
    headers = [
        "Id работы", "Автор", "Фамилия", "Имя", "Кодовое слово",
        "Результат", "Орф.\n ошибки", "Пункт.\n ошибки", "Скан работы"
    ]
    for col, text in enumerate(headers):
        cell = ws.cell(row=1, column=col+1, value=text)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[cell.column_letter].width = colums_width[col]
    ws.row_dimensions[1].height = 50

def insert_images_to_excel(pdf_folder, output_excel):
    wb = Workbook()
    ws = wb.active

    prepare_excel(ws)

    for row, filename in enumerate(os.listdir(pdf_folder),start=2):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(pdf_folder, filename)
        upload_tasks.append(async_save_to_yandex_disk("/output",pdf_path))
        print(f"Начало Обработки: {filename}")
        images = crop_image_by_pixels(pdf_path)

        cell = ws.cell(row=row, column=1, value=os.path.splitext(filename)[0])
        cell.alignment = Alignment(horizontal="center", vertical="center")

        for col, img_buf in enumerate(images, start=2):
            if col == 3:
                col=6
            cell = ws.cell(row=row, column=col)
            ws.add_image(XLImage(img_buf), cell.coordinate)

        ws.row_dimensions[row].height = 84
        row += 1
        print(f"Конец Обработки: {filename}")

    wb.save(output_excel)
    save_to_yandex_disk("/xlsx", output_excel)


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

loop.run_until_complete(asyncio.gather(*upload_tasks))

end = time.time()
print(f"⏱ Выполнено за {end - start:.2f} секунд")
