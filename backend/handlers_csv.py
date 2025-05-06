from flask import request, jsonify, send_file, make_response
import os, shutil
import time
import base64
import tempfile
import zipfile
from multiprocessing import Pool, cpu_count
import asyncio
from pathlib import Path
from io import BytesIO
import logging
import yadisk
import json

y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))
SITY = ["Moscow", "Novosibirsk", "Kazan"]

def register_routes_csv(app):
    @app.route("/upload-excel", methods=["POST"])
    def upload_xlsx_files():
        sity = request.form.get("sity")
        files = request.files.getlist("files")
        if not sity or sity not in SITY:
            return jsonify({"error": "Неверный или отсутствующий город"}), 400
        if not files:
            return jsonify({"error": "Нет файлов для загрузки"}), 400
        folder_path = f"/{sity}_xlsx/verified"
        if not y.exists(folder_path):
            y.mkdir(folder_path)
        success, failed = [], []
        for file in files:
            filename = file.filename
            if not filename.lower().endswith(".xlsx"):
                failed.append(filename)
                continue
            try:
                temp_path = os.path.join(tempfile.gettempdir(), filename)
                file.save(temp_path)
                remote_filepath = f"{folder_path}/{filename}"
                if y.exists(remote_filepath):
                    y.remove(remote_filepath, permanently=True)
                    time.sleep(1)
                y.upload(temp_path, remote_filepath)
                success.append(filename)
            except Exception as e:
                logging.error(f"Ошибка при загрузке {filename}: {e}")
                failed.append(filename)
        return jsonify({"uploaded": success, "failed": failed})

    @app.route("/process-excel", methods=["POST"])
    def post_processing():
        data = request.get_json()
        sity = data.get("sity")
        logging.info(f"Запрос на постобработку города: {sity}")
        try:
            start = time.time()
            status, processed, duplicates, failed, logs = process_city(sity)
            duration = time.time() - start

            log_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8")
            log_file.write("\n".join(logs))
            log_file.close()

            result_json = {
                "status": status,
                "processed": processed,
                "duplicates": duplicates,
                "failed": failed,
                "duration_sec": round(duration, 2)
            }

            encoded = base64.b64encode(json.dumps(result_json).encode("utf-8")).decode("ascii")

            response = make_response(send_file(log_file.name, as_attachment=True, download_name=f"{sity}_log.txt"))
            response.headers["X-Result-Json"] = encoded
            return response

        except Exception as e:
            logging.error(f"Что-то пошло не так, error: {str(e)}")
            return jsonify({"status": "Что-то пошло не так", "error": str(e)}), 500

    @app.route("/csv-list", methods=["GET"])
    def list_csv_files():
        sity = request.args.get("sity")
        if not sity or sity not in SITY:
            return jsonify({"error": "Неверный или отсутствующий город"}), 400
        folder_path = f"/{sity}_csv"
        try:
            if not y.exists(folder_path):
                return jsonify({"files": []})
            files = y.listdir(folder_path)
            csv_files = sorted(
                [f for f in files if f["type"] == "file" and f["name"].endswith(".csv")],
                key=lambda f: f["created"],
                reverse=True
            )
            file_names = [os.path.splitext(f["name"])[0] for f in csv_files]
            return jsonify({"files": file_names})
        except Exception as e:
            logging.error(f"Ошибка при получении файлов: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/download-csv", methods=["POST"])
    def download_csv_files():
        data = request.get_json()
        sity = data.get("sity")
        files = data.get("files", [])
        if not sity or not isinstance(files, list) or not files:
            return jsonify({"error": "Некорректные данные запроса"}), 400
        remote_folder = f"/{sity}_csv"
        done_folder = f"{remote_folder}/done"
        if not y.exists(done_folder):
            y.mkdir(done_folder)
        zip_buffer = BytesIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for name in files:
                    csv_filename = f"{name}.csv"
                    remote_csv_path = f"{remote_folder}/{csv_filename}"
                    local_csv_path = os.path.join(tmpdir, csv_filename)
                    done_csv_path = f"{done_folder}/{csv_filename}"
                    try:
                        y.download(remote_csv_path, local_csv_path)
                        if y.exists(done_csv_path):
                            y.remove(done_csv_path, permanently=True)

                        zipf.write(local_csv_path, arcname=csv_filename)
                        logging.info(f"✅ CSV добавлен в архив: {csv_filename}")
                    except Exception as e:
                        logging.error(f"❌ Ошибка при скачивании CSV: {csv_filename}: {e}")

                    remote_pdf_folder = f"{remote_folder}/{name}"
                    pdf_zip_filename = f"{name}.zip"
                    local_pdf_zip = f"{sity}_csv/{name}.zip"
                    extracted_folder = f"{sity}_csv/{name}"

                    try:
                        y.download(remote_pdf_folder, local_pdf_zip)

                        # Распаковка в папку
                        with zipfile.ZipFile(local_pdf_zip, 'r') as zip_ref:
                            zip_ref.extractall(extracted_folder)

                        # Удаляем оригинальный zip после распаковки
                        os.remove(local_pdf_zip)

                        # Собираем без вложенности в новый zip
                        with zipfile.ZipFile(local_pdf_zip, 'w', zipfile.ZIP_DEFLATED) as temp_zip:
                            for root, dirs, files in os.walk(extracted_folder):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    arcname = f"{file}"  # без вложенности
                                    temp_zip.write(file_path, arcname=arcname)

                        done_pdf_folder = f"{done_folder}/{name}"
                        if y.exists(done_pdf_folder):
                            y.remove(done_pdf_folder, permanently=True)
                        y.move(remote_pdf_folder, done_pdf_folder)
                        y.move(remote_csv_path, done_csv_path)

                        # Добавляем этот архив в общий архив на отправку
                        zipf.write(local_pdf_zip, arcname=pdf_zip_filename)
                        logging.info(f"✅ PDF-файлы добавлены как {pdf_zip_filename}")

                    except Exception as e:
                        logging.error(f"❌ Ошибка при обработке PDF-папки {name}: {e}")

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{sity}_csv_selected.zip"
        )

def makedirs(sity):
    pdf_folder = f"{sity}_pdf"
    csv_folder = f"{sity}_csv"
    if not y.exists(pdf_folder):
        y.mkdir(pdf_folder)
        time.sleep(0.5)
    if not y.exists(csv_folder):
        y.mkdir(csv_folder)
    os.makedirs(csv_folder, exist_ok=True)
    time.sleep(1)

def check_duplicates(sity, name):
    pdf_folder = f"{sity}_pdf/{name}"
    if os.path.exists(pdf_folder):
        shutil.rmtree(pdf_folder)
    Path(pdf_folder).mkdir(parents=True, exist_ok=True)
    if not y.exists(pdf_folder):
        y.mkdir(pdf_folder)
    else:
        xlsx_file = f"{sity}_xlsx/done/{name}.xlsx"
        if y.exists(xlsx_file):
            logging.info(f"Дубликат Excel-файла на диске: {xlsx_file}")
            y.remove(xlsx_file, permanently=True)
            return True
        csv_file = f"{sity}_csv/{name}.csv"
        if y.exists(csv_file):
            logging.info(f"Дубликат Csv-файла на диске: {csv_file}")
            y.remove(csv_file, permanently=True)
            return True
    return False

def run_async_process_csv(sity, name):
    import csv_processor as csv
    try:
        result = asyncio.run(csv.process_csv(sity, name))
        return result
    except Exception as e:
        return {"status": "error", "name": name, "logs": [f"Ошибка {name}: {str(e)}"]}

def process_city(sity: str):
    if sity not in SITY:
        return f"Город не из списка: {SITY}", [], [], [], []

    folder_path = f"/{sity}_xlsx/verified"
    if not y.exists(folder_path):
        return f"Папка '{folder_path}' не найдена на Яндекс.Диске.", [], [], [], []

    makedirs(sity)
    tasks = []
    duplicates = []
    processed = []
    failed_tasks = []
    all_logs = []

    for item in y.listdir(folder_path):
        if item["type"] == "file" and item["name"].lower().endswith(".xlsx"):
            filename = item["name"]
            name = os.path.splitext(filename)[0]
            if check_duplicates(sity, name):
                duplicates.append(name)
            tasks.append((sity, name))

    if not tasks:
        return "Нет файлов для обработки.", [], [], [], []

    with Pool(cpu_count()) as pool:
        results = pool.starmap(run_async_process_csv, tasks)

    for res in results:
        all_logs.extend(res.get("logs", []))
        if res["status"] == "success":
            processed.append(res["name"])
        elif res["status"] == "skipped":
            failed_tasks.append({"name": res["name"], "error": "пропущены орфографические ошибки"})
        else:
            failed_tasks.append({"name": res["name"], "error": res.get("error", "unknown")})

    return "Файлы обработаны", processed, duplicates, failed_tasks, all_logs
