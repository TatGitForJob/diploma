from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import time
import yadisk
from multiprocessing import Pool, cpu_count
from pathlib import Path
import asyncio
import logging
from datetime import datetime
import tempfile
import zipfile
from io import BytesIO

app = Flask("Diploma")
CORS(app)

y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))

SITY = ["Moscow",  "Novosibirsk"]


os.makedirs("logs", exist_ok=True)
log_filename = datetime.now().strftime("logs/app_%Y-%m-%d.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger("yadisk").setLevel(logging.WARNING)

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
        return pdf_folder, True

    return pdf_folder, False

def run_async_process_pdf(sity, name, pdf_folder, xlsx_folder):
    import pdf_processor as pdf
    asyncio.run(pdf.process_pdf(sity, name, pdf_folder, xlsx_folder))

def process_city(sity: str) -> tuple[str, list[str], list[str]]:
    if sity not in SITY:
        return f"Город не из списка: {SITY}", [],[]

    folder_path = f"/{sity}"
    if not y.exists(folder_path):
        return f"Папка '{folder_path}' не найдена на Яндекс.Диске.", [], []

    done_folder = f"{folder_path}/done"
    if not y.exists(done_folder):
        y.mkdir(done_folder)

    xlsx_folder = makedirs(sity)
    tasks = []
    duplicates = []
    processed = []

    for item in y.listdir(folder_path):
        if item["type"] == "file" and item["name"].lower().endswith(".pdf"):
            filename = item["name"]
            name = os.path.splitext(filename)[0]
            if len(name) != 5:
                logging.error(f"Имя файла не длины 5: /{sity}/{name}.pdf")
                continue
            logging.info(f"Обработка файла: /{sity}/{name}.pdf")
            pdf_folder, duplicate = check_duplicates(sity, name)
            if duplicate:
                duplicates.append(pdf_folder)
            else:
                processed.append(pdf_folder)
            tasks.append((sity, name, pdf_folder, xlsx_folder))

    if not tasks:
        return "Нет файлов для обработки.", [], []

    with Pool(cpu_count()) as pool:
        pool.starmap(run_async_process_pdf, tasks)

    return "Файлы обработаны", processed, duplicates

@app.route("/process", methods=["POST"])
def trigger_processing():
    data = request.get_json()
    sity = data.get("sity")
    logging.info(f"➡️ Запрос на обработку города: {sity}")
    try:
        start = time.time()
        status, processed, duplicates = process_city(sity)
        duration = time.time() - start
        logging.info("Успешный запрос процессинга")
        return jsonify({"status": status, "processed": processed, "duplicates": duplicates, "duration_sec": round(duration, 2)})
    except Exception as e:
        logging.error(f"Что-то пошло не так, error: {str(e)}")
        return jsonify({"status": "Что-то пошло не так", "error": str(e)}), 500

@app.route("/xlsx-list", methods=["GET"])
def list_xlsx_files():
    sity = request.args.get("sity")

    if not sity or sity not in SITY:
        logging.warning("Запрос с неверным или отсутствующим городом: %s", sity)
        return jsonify({"error": "Неверный или отсутствующий город"}), 400

    folder_path = f"/{sity}_xlsx"
    logging.info(f"📂 Получение списка xlsx файлов в папке: {folder_path}")

    try:
        if not y.exists(folder_path):
            logging.info(f"Папка не найдена: {folder_path}")
            return jsonify({"files": []})

        files = y.listdir(folder_path)

        xlsx_files = sorted(
            [f for f in files if f["type"] == "file" and f["name"].endswith(".xlsx")],
            key=lambda f: f["created"],
            reverse=True
        )

        file_names = [f["name"] for f in xlsx_files]
        logging.info(f"Найдено {len(file_names)} файлов: {file_names}")
        return jsonify({"files": file_names})

    except Exception as e:
        logging.error(f"Ошибка при получении файлов: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/download-xlsx", methods=["POST"])
def download_xlsx_files():
    data = request.get_json()
    sity = data.get("sity")
    files = data.get("files", [])
    logging.info(f"Запрошены excel на скачивание: {files}")

    if not sity or not isinstance(files, list) or not files:
        return jsonify({"error": "Некорректные данные запроса"}), 400

    remote_folder = f"/{sity}_xlsx"
    zip_buffer = BytesIO()

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for filename in files:
                remote_path = f"{remote_folder}/{filename}"
                local_path = os.path.join(tmpdir, filename)

                try:
                    y.download(remote_path, local_path)
                    done_folder = f"{remote_folder}/done"
                    if not y.exists(done_folder):
                        y.mkdir(done_folder)
                    done_filename = f"{done_folder}/{filename}"
                    if y.exists(done_filename):
                        y.remove(done_filename, permanently=True)
                    y.move(remote_path, done_filename)
                    zipf.write(local_path, arcname=filename)
                except Exception as e:
                    logging.error(f"Ошибка при скачивании {filename}: {e}")

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{sity}_xlsx_selected.zip"
    )

@app.route("/upload-pdf", methods=["POST"])
def upload_pdf_files():
    sity = request.form.get("sity")
    files = request.files.getlist("files")

    if not sity or sity not in SITY:
        logging.error(f"Неверный или отсутствующий город: {sity}")
        return jsonify({"error": "Неверный или отсутствующий город"}), 400

    if not files:
        logging.error("Нет файлов в запросе")
        return jsonify({"error": "Нет файлов для загрузки"}), 400

    folder_path = f"/{sity}"
    if not y.exists(folder_path):
        y.mkdir(folder_path)

    success, failed = [], []

    for file in files:
        filename = file.filename
        if not filename.lower().endswith(".pdf") or len(os.path.splitext(filename)[0]) != 5:
            failed.append(filename)
            continue

        logging.info(f"Начата Загрузка файла: {filename}")
        try:
            temp_path = os.path.join(tempfile.gettempdir(), filename)
            file.save(temp_path)
            remote_filepath = f"{folder_path}/{filename}"
            if y.exists(remote_filepath):
                logging.info(f"Дубликат файла: {filename}")
                y.remove(remote_filepath, permanently=True)
            y.upload(temp_path, remote_filepath)
            logging.info(f"Загружен файл: {filename}")
            success.append(filename)
        except Exception as e:
            logging.error(f"Ошибка при загрузке {filename}: {e}")
            failed.append(filename)

    return jsonify({
        "uploaded": success,
        "failed": failed,
        "status": f"Загружено: {len(success)}, Ошибки: {len(failed)}"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
