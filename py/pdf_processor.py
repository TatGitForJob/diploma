import os, asyncio
from concurrent.futures import ThreadPoolExecutor
from openpyxl import Workbook
from PyPDF2 import PdfReader, PdfWriter
import yadisk
import excel_filler as excel

y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))

def save_to_yandex_disk(file_path):
    y.upload(file_path, file_path)
    y.publish(file_path)
    print(f"✅ Загружено: {file_path}")

async def async_save_to_yandex_disk(file_path, loop, executor):
    await loop.run_in_executor(executor, save_to_yandex_disk, file_path)

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

def natural_sort_key(filename):
    return int(filename.split('_')[1].split('.')[0])

async def process_excel(pdfs_folder, excel_path):
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()
    tasks = []

    wb = Workbook()
    ws = wb.active
    excel.prepare_excel(ws)
    row = 2
    for filename in sorted(os.listdir(pdfs_folder), key=natural_sort_key):
        if not filename.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(pdfs_folder, filename)
        tasks.append(async_save_to_yandex_disk(pdf_path, loop, executor))
        excel.fill_text_cells(ws,row,filename)
        excel.fill_image_cells(ws,row,pdf_path)
        row += 1
    await asyncio.gather(*tasks)

    #save_pdf_links(ws,"/output")
    print("DBG")
    wb.save(excel_path)
    save_to_yandex_disk(excel_path)

async def process_pdf(sity,name,pdf_folder,xlsx_folder):
    pdf_file_path=f"{pdf_folder}/{name}.pdf"
    y.download(f"/{sity}/{name}.pdf", pdf_file_path)
    
    split_pdf_by_pages(pdf_file_path, pdf_folder)
    await process_excel(pdf_folder, f"{xlsx_folder}/{name}.xlsx")
    y.move(f"/{sity}/{name}.pdf", f"/{sity}/done/{name}.pdf")
    y.close()
