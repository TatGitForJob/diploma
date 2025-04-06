import sys,asyncio,os,time
import yadisk
import pdf_processor as pdf

y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))

def mkdir_and_check_duplicates(sity,name):
    pdf_folder=f"{sity}_pdf"
    xlsx_folder=f"{sity}_xlsx"
    if not y.exists(pdf_folder):
        y.mkdir(pdf_folder)
    if not y.exists(xlsx_folder):
        y.mkdir(xlsx_folder)
    pdf_folder=f"{sity}_pdf/{name}"
    os.makedirs(pdf_folder, exist_ok=True)
    os.makedirs(xlsx_folder, exist_ok=True)
    if not y.exists(pdf_folder):
        y.mkdir(pdf_folder)
    else:
        print(f"Дубликат директория на диске: {pdf_folder}:")
        return "","",False
    xlsx_file=f"{sity}_xlsx/{name}.xlsx"
    if y.exists(xlsx_file):
        print(f"Дубликат excel файл на диске: {xlsx_file}:")
        return "","",False
    return pdf_folder,xlsx_folder,True

async def main():
    if len(sys.argv) < 2:
        print("Укажи название города на Яндекс.Диске, например:")
        return

    sity = sys.argv[1]
    if sity not in ["Moscow","Piter","Novgorod"]:
        print("город не из: ","Moscow ","Piter ","Novgorod")
        return
    folder_path=f"/{sity}"

    if not y.exists(folder_path):
        print(f"Папка '{folder_path}' не найдена на Яндекс.Диске.")
        
    done_folder=f"{folder_path}/done"
    if not y.exists(done_folder):
        y.mkdir(done_folder)

    tasks = []

    for item in y.listdir(folder_path):
        if item["type"] == "file" and item["name"].lower().endswith(".pdf"):
            filename = item["name"]
            name = os.path.splitext(filename)[0]
            print(f"📄 Обработка файла: {name}")
            pdf_folder,xlsx_folder,ok = mkdir_and_check_duplicates(sity,name)
            if ok:
                tasks.append(pdf.process_pdf(sity,name,pdf_folder,xlsx_folder))
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main())
    print(f"⏱ Выполнено за {time.time() - start:.2f} секунд")
    y.close()
