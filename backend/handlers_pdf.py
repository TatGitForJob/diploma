
from flask import request, jsonify, send_file
import os
import time
import tempfile
import zipfile
import asyncio
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path
from io import BytesIO
import logging
import yadisk

y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))
SITY = ["Moscow",  "Novosibirsk"]

def register_routes_pdf(app):
    @app.route("/upload-pdf", methods=["POST"])
    def upload_pdf_files():
        sity = request.form.get("sity")
        files = request.files.getlist("files")
        if not sity or sity not in SITY:
            return jsonify({"error": "Неверный или отсутствующий город"}), 400
        if not files:
            return jsonify({"error": "Нет файлов для загрузки"}), 400
        folder_path = f"/{sity}"
        if not y.exists(folder_path):
            y.mkdir(folder_path)
        success, failed = [], []
        for file in files:
            filename = file.filename
            if not filename.lower().endswith(".pdf"):
                failed.append(filename)
                continue
            try:
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                file.save(temp_path)
                remote_filepath = f"{folder_path}/{filename}"
                if y.exists(remote_filepath):
                    y.remove(remote_filepath, permanently=True)
                y.upload(temp_path, remote_filepath)
                success.append(filename)
            except Exception as e:
                logging.error(f"Ошибка при загрузке {filename}: {e}")
                failed.append(filename)
        return jsonify({"uploaded": success, "failed": failed})

    @app.route("/process-pdf", methods=["POST"])
    def pre_processing():
        data = request.get_json()
        sity = data.get("sity")
        logging.info(f"➡️ Запрос на обработку города: {sity}")
        try:
            start = time.time()
            status, processed, duplicates, failed = process_city(sity)
            duration = time.time() - start
            logging.info("Успешный запрос процессинга")
            return jsonify({
                "status": status,
                "processed": processed,
                "duplicates": duplicates,
                "failed": failed,
                "duration_sec": round(duration, 2)
            })
        except Exception as e:
            logging.error(f"Что-то пошло не так, error: {str(e)}")
            return jsonify({"status": "Что-то пошло не так", "error": str(e)}), 500


def makedirs(sity):
    pdf_folder = f"{sity}_pdf"
    xlsx_folder = f"{sity}_xlsx"
    if not y.exists(pdf_folder):
        y.mkdir(pdf_folder)
        time.sleep(0.5)
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
        logging.info(f"Дубликат директории на диске: {pdf_folder}")
        y.remove(pdf_folder, permanently=True)
        time.sleep(1)
        y.mkdir(pdf_folder)
        xlsx_file = f"{sity}_xlsx/{name}.xlsx"
        if y.exists(xlsx_file):
            logging.info(f"Дубликат Excel-файла на диске: {xlsx_file}")
            y.remove(xlsx_file, permanently=True)
        xlsx_downloaded_file = f"{sity}_xlsx/downloaded/{name}.xlsx"
        if y.exists(xlsx_downloaded_file):
            logging.info(f"Дубликат Excel-файла на диске в выгруженных: {xlsx_downloaded_file}")
            y.remove(xlsx_downloaded_file, permanently=True)
        return pdf_folder, True
    return pdf_folder, False

def run_async_process_pdf(sity, name, pdf_folder, xlsx_folder):
    import pdf_processor as pdf
    try:
        asyncio.run(pdf.process_pdf(sity, name, pdf_folder, xlsx_folder))
        return { "name": name, "status": "success" }
    except Exception as e:
        return { "name": name, "status": "error", "error": str(e) }

def process_city(sity: str) -> tuple[str, list[str], list[str], list[dict]]:
    if sity not in SITY:
        return f"Город не из списка: {SITY}", [], [], []

    folder_path = f"/{sity}"
    if not y.exists(folder_path):
        return f"Папка '{folder_path}' не найдена на Яндекс.Диске.", [], [], []

    done_folder = f"{folder_path}/done"
    if not y.exists(done_folder):
        y.mkdir(done_folder)

    xlsx_folder = makedirs(sity)
    tasks = []
    duplicates = []
    processed = []
    failed_tasks = []

    for item in y.listdir(folder_path):
        if item["type"] == "file" and item["name"].lower().endswith(".pdf"):
            filename = item["name"]
            name = os.path.splitext(filename)[0]
            logging.info(f"Обработка файла: /{sity}/{name}.pdf")
            pdf_folder, duplicate = check_duplicates(sity, name)
            if duplicate:
                duplicates.append(name)
            tasks.append((sity, name, pdf_folder, xlsx_folder))

    if not tasks:
        return "Нет файлов для обработки.", [], [], []

    results = []
    with Pool(cpu_count()) as pool:
        results = pool.starmap(run_async_process_pdf, tasks)

    for res in results:
        if res["status"] == "success":
            processed.append(res["name"])
        else:
            err = { "name": res["name"], "error": res["error"] }
            logging.error("Ошибка при процессинге pdf: %s", str(err))
            failed_tasks.append(err)

    return "Файлы обработаны", processed, duplicates, failed_tasks