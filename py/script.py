# вверху файла
import os
import fitz
import shutil
import time
import asyncio
import io
from concurrent.futures import ThreadPoolExecutor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
import yadisk

# Конфигурация
YANDEX_TOKEN = "y0__xDG74akqveAAhjblgMggf6o1xKS9mEBdAxviZ1aAoqtrPku2rA5qA"
REMOTE_PDF_PATH = "/input/34329.pdf"
LOCAL_PDF_PATH = "../pdfs/34329.pdf"
PDF_OUTPUT_FOLDER = "../pdfs"
EXCEL_OUTPUT_PATH = "out.xlsx"
CROPS = [(25, 90, 400, 200), (410, 90, 600, 200)]
COLUMN_WIDTHS = [20, 54, 20, 20, 20, 28, 10, 10, 70]


def save_to_yandex_disk(y, save_folder, file_path):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    if not y.exists(save_folder):
        y.mkdir(save_folder)
    i = 1
    while y.exists(f"{save_folder}/{filename}"):
        filename = f"{name} ({i}){ext}"
        i += 1
    y.upload(file_path, f"{save_folder}/{filename}")
    print(f"✅ Загружено: {filename}")


async def async_save_to_yandex_disk(y, folder, path, loop, executor):
    await loop.run_in_executor(executor, save_to_yandex_disk, y, folder, path)


def crop_image_by_pixels(pdf_path, crops):
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=75)
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    parts = []
    for left, top, right, bottom in crops:
        cropped = image.crop((left, top, right, bottom))
        buf = io.BytesIO()
        cropped.save(buf, format='PNG')
        parts.append(buf)
    return parts


def split_pdf_by_pages(input_pdf_path, output_folder, chunk_size=2):
    filename = os.path.splitext(os.path.basename(input_pdf_path))[0]
    reader = PdfReader(input_pdf_path)
    total_pages = len(reader.pages)
    os.makedirs(output_folder, exist_ok=True)
    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        for j in range(i, min(i + chunk_size, total_pages)):
            writer.add_page(reader.pages[j])
        part_filename = os.path.join(output_folder, f"{filename}_{i//chunk_size}.pdf")
        with open(part_filename, "wb") as f_out:
            writer.write(f_out)
    os.remove(input_pdf_path)


def prepare_excel(ws, col_widths):
    headers = [
        "Id работы", "Автор", "Фамилия", "Имя", "Кодовое слово",
        "Результат", "Орф.\n ошибки", "Пункт.\n ошибки", "Скан работы"
    ]
    for col, text in enumerate(headers):
        cell = ws.cell(row=1, column=col + 1, value=text)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(col + 1)].width = col_widths[col]
    ws.row_dimensions[1].height = 50


async def insert_images_to_excel(y, pdf_folder, output_excel, crops, col_widths, loop, executor):
    wb = Workbook()
    ws = wb.active
    prepare_excel(ws, col_widths)
    row = 2
    tasks = []

    for filename in sorted(os.listdir(pdf_folder)):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(pdf_folder, filename)
        tasks.append(async_save_to_yandex_disk(y, "/output", pdf_path, loop, executor))
        cell = ws.cell(row=row, column=1, value=os.path.splitext(filename)[0])
        cell.alignment = Alignment(horizontal="center", vertical="center")

        images = crop_image_by_pixels(pdf_path, crops)
        for col, img_buf in enumerate(images, start=2):
            if col == 3:
                col = 6
            img = XLImage(img_buf)
            cell = ws.cell(row=row, column=col)
            ws.add_image(img, cell.coordinate)

        ws.row_dimensions[row].height = 84
        row += 1

    wb.save(output_excel)
    tasks.append(async_save_to_yandex_disk(y, "/xlsx", output_excel, loop, executor))
    return tasks


async def main():
    start = time.time()
    print("⬇️ Старт обработки...")

    shutil.rmtree(PDF_OUTPUT_FOLDER, ignore_errors=True)
    os.makedirs(PDF_OUTPUT_FOLDER, exist_ok=True)

    y = yadisk.YaDisk(token=YANDEX_TOKEN)
    y.download(REMOTE_PDF_PATH, LOCAL_PDF_PATH)

    split_pdf_by_pages(LOCAL_PDF_PATH, PDF_OUTPUT_FOLDER)

    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()
    upload_tasks = await insert_images_to_excel(
        y, PDF_OUTPUT_FOLDER, EXCEL_OUTPUT_PATH,
        crops=CROPS,
        col_widths=COLUMN_WIDTHS,
        loop=loop,
        executor=executor
    )

    await asyncio.gather(*upload_tasks)

    end = time.time()
    print(f"⏱ Выполнено за {end - start:.2f} секунд")


if __name__ == "__main__":
    asyncio.run(main())
