import sys
import os
import time
import yadisk
from multiprocessing import Pool, cpu_count
from pathlib import Path

y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))

def makedirs(sity):
    pdf_folder = f"{sity}_pdf"
    xlsx_folder = f"{sity}_xlsx"
    if not y.exists(pdf_folder):
        y.mkdir(pdf_folder)
    if not y.exists(xlsx_folder):
        y.mkdir(xlsx_folder)
    os.makedirs(xlsx_folder, exist_ok=True)
    time.sleep(1)
    return xlsx_folder

def check_duplicates(sity, name):
    pdf_folder = f"{sity}_pdf/{name}"
    Path(pdf_folder).mkdir(parents=True, exist_ok=True)

    if not y.exists(pdf_folder):
        y.mkdir(pdf_folder)
    else:
        print(f"Дубликат директории на диске: {pdf_folder}")
        return "", False

    xlsx_file = f"{sity}_xlsx/{name}.xlsx"
    if y.exists(xlsx_file):
        print(f"Дубликат Excel-файла на диске: {xlsx_file}")
        return "", False

    return pdf_folder, True


def run_async_process_pdf(sity, name, pdf_folder, xlsx_folder):
    import asyncio
    import pdf_processor as pdf  # импорт внутри процесса
    asyncio.run(pdf.process_pdf(sity, name, pdf_folder, xlsx_folder))

def main():
    if len(sys.argv) < 2:
        print("Укажи название города на Яндекс.Диске, например:")
        return

    sity = sys.argv[1]
    if sity not in ["Moscow", "Piter", "Novgorod"]:
        print("Город не из списка: Moscow, Piter, Novgorod")
        return

    folder_path = f"/{sity}"

    if not y.exists(folder_path):
        print(f"Папка '{folder_path}' не найдена на Яндекс.Диске.")
        return

    done_folder = f"{folder_path}/done"
    if not y.exists(done_folder):
        y.mkdir(done_folder)

    xlsx_folder = makedirs(sity)
    tasks = []

    for item in y.listdir(folder_path):
        if item["type"] == "file" and item["name"].lower().endswith(".pdf"):
            filename = item["name"]
            name = os.path.splitext(filename)[0]
            print(f"Обработка файла: /{sity}/{name}.pdf")
            pdf_folder, ok = check_duplicates(sity, name)
            if ok:
                tasks.append((sity, name, pdf_folder, xlsx_folder))

    with Pool(cpu_count()) as pool:
        pool.starmap(run_async_process_pdf, tasks)

if __name__ == "__main__":
    start = time.time()
    main()
    print(f"Выполнено за {time.time() - start:.2f} секунд")
    y.close()
