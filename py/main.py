import os, time, shutil, asyncio
from concurrent.futures import ThreadPoolExecutor
from openpyxl import Workbook
from PyPDF2 import PdfReader, PdfWriter
import yadisk
import excel_filler as excel

# Конфигурация
YANDEX_TOKEN = "y0__xCg-LqmBhjblgMg4LuN3hIYWcHG7vB3EnF3siKkWEK40i7ZiA"
CLASS = "34329"
SITY = "Moscow"

y = yadisk.YaDisk(token=YANDEX_TOKEN)

def save_pdf_to_yandex_disk( remote_folder, file_path):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    if not y.exists(remote_folder):
        y.mkdir(remote_folder) 
    remote_folder=f"{remote_folder}/{name}"
    if not y.exists(remote_folder):
        y.mkdir(remote_folder)
    else:
        print(f"Дубликат аудитория {name}:")

    i = 1
    while y.exists(f"{remote_folder}/{filename}"):
        filename = f"{name} _{i}{ext}"
        i += 1
    y.upload(file_path, f"{remote_folder}/{filename}")
    y.publish(f"{remote_folder}/{filename}")
    print(f"✅ Загружено: {filename}")

async def async_save_to_yandex_disk(folder, file_path, loop, executor):
    await loop.run_in_executor(executor, save_pdf_to_yandex_disk, folder, file_path)

def save_to_yandex_disk( remote_folder, file_path):
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    if not y.exists(remote_folder):
        y.mkdir(remote_folder)

    i = 1
    while y.exists(f"{remote_folder}/{filename}"):
        filename = f"{name} _{i}{ext}"
        i += 1
    y.upload(file_path, f"{remote_folder}/{filename}")
    print(f"✅ Загружено: {filename}")

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

#def save_pdf_links(ws,pdf_files_path):
    #print(ws,pdf_files_path)



async def process_excel(pdfs_folder, excel_path):
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()
    tasks = []

    wb = Workbook()
    ws = wb.active
    excel.prepare_excel(ws)
    row = 2
    for filename in sorted(os.listdir(pdfs_folder), key=excel.natural_sort_key):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(pdfs_folder, filename)
        tasks.append(async_save_to_yandex_disk("/output", pdf_path, loop, executor))
        excel.fill_text_cells(ws,row,filename)
        excel.fill_image_cells(ws,row,pdf_path)
        row += 1
    await asyncio.gather(*tasks)

    #save_pdf_links(ws,"/output")

    wb.save(excel_path)
    save_to_yandex_disk("/xlsx", excel_path)

async def main():
    start = time.time()
    print("⬇️ Старт обработки...")

    pdf_folder=f"../pdfs/{CLASS}"
    xlsx_folder="../xlsx"
    pdf_file_path=f"{pdf_folder}/{CLASS}.pdf"

    shutil.rmtree(pdf_folder, ignore_errors=True)
    shutil.rmtree(xlsx_folder, ignore_errors=True)
    os.makedirs(pdf_folder, exist_ok=True)
    os.makedirs(xlsx_folder, exist_ok=True)


    y.download(f"/{SITY}/{CLASS}.pdf", pdf_file_path)

    split_pdf_by_pages(pdf_file_path, pdf_folder)

    await process_excel(pdf_folder, f"{xlsx_folder}/{CLASS}.xlsx")

    print(f"⏱ Выполнено за {time.time() - start:.2f} секунд")
    y.close()


if __name__ == "__main__":
    asyncio.run(main())
