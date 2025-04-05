import os, time, shutil, asyncio
from concurrent.futures import ThreadPoolExecutor
from openpyxl import Workbook
from PyPDF2 import PdfReader, PdfWriter
import yadisk
import excel_filler as excel

# Конфигурация
YANDEX_TOKEN = "y0__xCg-LqmBhjblgMg4LuN3hIYWcHG7vB3EnF3siKkWEK40i7ZiA"
YANDEX_ID = "1130000065607622"
REMOTE_PDF_PATH = "/Moscow/77777.pdf"
LOCAL_PDF_PATH = "../pdfs/77777.pdf"
PDF_OUTPUT_FOLDER = "../pdfs"
EXCEL_OUTPUT_PATH = "out.xlsx"

def save_to_yandex_disk(y, folder, file_path):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    if not y.exists(folder):
        y.mkdir(folder)


    i = 1
    while y.exists(f"{folder}/{filename}"):
        filename = f"{name} _{i}{ext}"
        i += 1
    y.upload(file_path, f"{folder}/{filename}")
    print(f"✅ Загружено: {filename}")

async def async_save_to_yandex_disk(y, folder, file_path, loop, executor):
    await loop.run_in_executor(executor, save_to_yandex_disk, y, folder, file_path)

def split_pdf_by_pages(input_pdf, out_folder, chunk_size=2):
    base = os.path.splitext(os.path.basename(input_pdf))[0]
    reader = PdfReader(input_pdf)
    os.makedirs(out_folder, exist_ok=True)
    for i in range(0, len(reader.pages), chunk_size):
        writer = PdfWriter()
        for page in reader.pages[i:i+chunk_size]:
            writer.add_page(page)
        with open(os.path.join(out_folder, f"{base}_{i//chunk_size}.pdf"), "wb") as f:
            writer.write(f)
    os.remove(input_pdf)

async def process_excel(y, pdfs_folder, excel_path, loop, executor):
    wb = Workbook()
    ws = wb.active
    excel.prepare_excel(ws)
    row = 2
    tasks = []

    for filename in sorted(os.listdir(pdfs_folder), key=excel.natural_sort_key):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(pdfs_folder, filename)
        tasks.append(async_save_to_yandex_disk(y, "/output", pdf_path, loop, executor))
        excel.fill_text_cells(ws,row,filename)
        excel.fill_image_cells(ws,row,pdf_path)
        row += 1
    wb.save(excel_path)
    tasks.append(async_save_to_yandex_disk(y, "/xlsx", excel_path, loop, executor))
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
    upload_tasks = await process_excel(
        y, PDF_OUTPUT_FOLDER, EXCEL_OUTPUT_PATH
        ,loop,executor
    )

    await asyncio.gather(*upload_tasks)

    print(f"⏱ Выполнено за {time.time() - start:.2f} секунд")


if __name__ == "__main__":
    asyncio.run(main())
