
import os
import threading
import logging
import time
import pandas as pd
import shutil
from PyPDF2 import PdfMerger
from zipfile import ZipFile
import yadisk

TRANSLIT = {'a':'а','b':'б','c':'ц','d':'д','e':'е','f':'ф','g':'г',
            'h':'х','i':'и','j':'й','k':'к','l':'л','m':'м','n':'н',
            'o':'о','p':'п','r':'р','s':'с','t':'т','u':'у','v':'в',
            'w':'вв','x':'кс','y':'ы','z':'з'}
NUMS = {'1':'один','2':'два','3':'три','4':'четыре',
        '5':'пять','6':'шесть','7':'семь',
        '8':'восемь','9':'девять','0':'ноль'}

CITY_CODEWORDS = {
    "Moscow": "тюлень",
    "Novosibirsk": "новосибирск"
}

y = yadisk.YaDisk(token=os.getenv("YANDEX_TOKEN"))

def download_and_extract_folder_as_zip(sity, site):
    remote_folder = f"{sity}_pdf/{site}"
    local_folder = f"{sity}_pdf/"
    local_zip = f"{site}.zip"

    if os.path.exists(remote_folder):
        shutil.rmtree(remote_folder)
    os.makedirs(remote_folder, exist_ok=True)

    try:
        y.download(remote_folder, local_zip)
        with ZipFile(local_zip, 'r') as zip_ref:
            zip_ref.extractall(local_folder)
        os.remove(local_zip)
        return f"{local_folder}{site}"
    except Exception as e:
        raise RuntimeError(f"Не удалось скачать и разархивировать PDF: {e}")

def fill_missing_identifiers(df, codeword):
    for col in ['Фамилия', 'Имя', 'Кодовое слово']:
        df[col] = df[col].fillna(codeword).replace('', codeword)
    return df

def check_missing_errors(df):
    cols = ['Орф. ошибки', 'Пункт. ошибки']
    has_null = df[cols].isnull().any().any()
    has_empty = (df[cols] == '').any().any()
    return has_null or has_empty

def merge_duplicate_pdfs(df, pdf_folder, log,site):
    duplicates = df[df.duplicated(['Фамилия','Имя','Кодовое слово'],keep=False)]
    merged = []
    for key, grp in duplicates.groupby(['Фамилия','Имя','Кодовое слово'],sort=False):
        merger = PdfMerger()
        parts = [site]
        for fid in grp['Id работы']:
            src = os.path.join(pdf_folder, f"{fid}.pdf")
            merger.append(src)
            os.remove(src)
            parts.extend(fid.split('_')[1].split('.')[0])
        new_name = "_".join(parts)
        dest = os.path.join(pdf_folder, f"{new_name}.pdf")
        merger.write(dest)
        merger.close()
        merged.append((grp.index[0], new_name, *key,
                       grp['Орф. ошибки'].iloc[0], grp['Пункт. ошибки'].iloc[0]))
        log.append(f"🔀 Объединены сканы: {grp['Id работы'].tolist()} → {new_name}")
    merged_df = pd.DataFrame(merged,
        columns=['index','Id работы','Фамилия','Имя','Кодовое слово','Орф. ошибки','Пункт. ошибки'])
    rest = df.drop(duplicates.index).copy()
    rest['index'] = rest.index
    rest = rest[['index','Id работы','Фамилия','Имя','Кодовое слово','Орф. ошибки','Пункт. ошибки']]
    return pd.concat([merged_df, rest], ignore_index=True).sort_values('index')

def normalize_and_explode(df, translit, nums, log,site):
    df = df.rename(columns={'Id работы':'id'}).reset_index(drop=True)
    for col in ['Фамилия','Имя','Кодовое слово']:
        df[col] = df[col].str.lower().str.split(',')
    df = df.explode("Фамилия").explode("Имя").explode("Кодовое слово")
    for mapping in (translit, nums):
        for k, v in mapping.items():
            for col in ['Фамилия', 'Имя', 'Кодовое слово']:
                before = df[col].copy()
                df[col] = df[col].replace(k, v, regex=True)
                if not df[col].equals(before):
                    log.append(f"🔤 Замена в файле {site} '{col}': {k} → {v}")
    df[['Фамилия','Имя','Кодовое слово']] = df[['Фамилия','Имя','Кодовое слово']].replace('[^ёа-я]','',regex=True)
    df['ФИО'] = df['Фамилия'] + ' ' + df['Имя']
    df['Скан'] = df['id'].astype(str)+'.pdf'
    return df[['ФИО','Орф. ошибки','Пункт. ошибки','Кодовое слово','Скан']]

def fire_and_forget_upload(path):
    def upload():
        try:
            if y.exists(path):
                y.remove(path, permanently=True)
            y.upload(path, path)
        except Exception as e:
            logging.warning(f"Фоновая загрузка не удалась: {e}")

    threading.Thread(target=upload).start()

async def process_csv(sity, site):
    logs = []

    try:
        start_time = time.time()
        codeword = CITY_CODEWORDS.get(sity)
        pdf_folder = download_and_extract_folder_as_zip(sity, site)
        xlsx_file = f"{sity}_xlsx/verified/{site}.xlsx"

        os.makedirs(os.path.dirname(xlsx_file), exist_ok=True)
        try:
            y.download(xlsx_file, xlsx_file)
        except Exception as e:
            raise FileNotFoundError(f"Не удалось скачать Excel с Яндекс.Диска: {e}")

        df = pd.read_excel(xlsx_file)
        df = df.rename(columns={'Орф.\n ошибки' : 'Орф. ошибки', 'Пункт.\n ошибки' : 'Пункт. ошибки'})
        df = fill_missing_identifiers(df, codeword)
        if check_missing_errors(df):
            logs.append(f"⚠️ В {site}.xlsx есть пропуски в колонках ошибок")
            return { "status": "skipped","name": site, "logs": logs }

        merged = merge_duplicate_pdfs(df, pdf_folder, logs,site)
        final_df = normalize_and_explode(merged, TRANSLIT, NUMS, logs,site)
        final_df = final_df.rename(columns={
        "Орф. ошибки": "Орфография",
        "Пункт. ошибки": "Пунктуация"
        })

        os.makedirs(f"./{sity}_csv", exist_ok=True)
        csv_path = f"{sity}_csv/{site}.csv"
        final_df.to_csv(csv_path, sep=';', encoding='cp1251', index=False)
        fire_and_forget_upload(csv_path)
        remote_pdf_folder = f"{sity}_csv/{site}"
        if y.exists(remote_pdf_folder):
            y.remove(remote_pdf_folder, permanently=True)
        y.mkdir(remote_pdf_folder)

        # Копируем PDF-файлы из локальной папки
        for fname in os.listdir(pdf_folder):
            full_path = os.path.join(pdf_folder, fname)
            remote_path = f"{remote_pdf_folder}/{fname}"
            y.upload(full_path, remote_path)

        logs.append(f"✅ Успешно обработан: {site} за {time.time()-start_time} секунд")
        logging.info(logs)

        done_folder = f"{sity}_xlsx/done"
        if not y.exists(done_folder):
            y.mkdir(done_folder)
        done_path = f"{done_folder}/{site}.xlsx"
        if y.exists(done_path):
            y.remove(done_path, permanently=True)
        y.move(xlsx_file, done_path)

        return {
            "status": "success",
            "name": site,
            "csv_path": f"/{sity}_csv/{site}.csv",
            "zip_path": f"/{sity}_csv/{site}.zip",
            "logs": logs
        }

    except Exception as e:
        logging.error(e)
        logs.append(f"❌ Ошибка при обработке {site}: {str(e)}")
        return { "status": "error", "name": site, "logs": logs }
