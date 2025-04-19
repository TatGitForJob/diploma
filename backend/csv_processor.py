import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from PyPDF2 import PdfMerger
from zipfile import ZipFile
import yadisk

# --- Configuration ---
CONFIG = {
    'codeword': 'гусь',
    'city_folder': 'москва',
    'year': '2024',
    'paths': {
        'submissions_local': "/content/drive/My Drive/2024/москва/файлы работ/",
        'log_sheet_csv_url': (
            "https://docs.google.com/spreadsheets/d/"
            "1PNK4su_Ie7IQBM-QAx1laKr1XqVjD3cqfObTCQAJGR0/"
            "export?format=csv&gid=1763744115"
        ),
        'final_local': "/content/drive/My Drive/2024/москва/загрузка на сайт"
    },
    'yandex': {
        'token_env': 'YANDEX_TOKEN',
        'remote_base': '/2024/москва'
    }
}

# --- Logging setup ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/process_sites.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- Yandex Disk client ---
y = yadisk.YaDisk(token=os.getenv(CONFIG['yandex']['token_env']))

def upload_to_yandex(local_path):
    """Upload a file and make it public."""
    remote_path = CONFIG['yandex']['remote_base'] + local_path.replace(":", "").replace("\\", "/")
    try:
        y.upload(local_path, remote_path)
        y.publish(remote_path)
        logger.info(f"Uploaded and published: {local_path} -> {remote_path}")
    except Exception as e:
        logger.error(f"Failed to upload {local_path}: {e}")
    return remote_path

async def async_upload(loop, executor, path):
    await loop.run_in_executor(executor, upload_to_yandex, path)

# --- Helpers ---
def read_global_log(csv_url):
    df = pd.read_csv(csv_url, dtype={'№ площадки': str})
    return df['№ площадки'].tolist()

def fill_missing_identifiers(df, codeword):
    for col in ['Фамилия', 'Имя', 'Кодовое слово']:
        df[col] = df[col].fillna(codeword).replace('', codeword)
    return df

def check_missing_errors(df):
    cols = ['Орф. ошибки', 'Пункт. ошибки']
    has_null = df[cols].isnull().any().any()
    has_empty = (df[cols] == '').any().any()
    return has_null or has_empty

def merge_duplicate_pdfs(df, submissions_path):
    duplicates = df[df.duplicated(['Фамилия','Имя','Кодовое слово'],keep=False)]
    merged = []
    for key, grp in duplicates.groupby(['Фамилия','Имя','Кодовое слово'],sort=False):
        merger = PdfMerger()
        parts = []
        for fid in grp['Id работы']:
            src = os.path.join(submissions_path, f"{fid}.pdf")
            merger.append(src)
            parts.extend(fid.split('_'))
        new_name = "_".join(parts)+".pdf"
        dest = os.path.join(submissions_path, new_name)
        merger.write(dest); merger.close()
        merged.append((grp.index[0], new_name, *key,
                       grp['Орф. ошибки'].iloc[0], grp['Пункт. ошибки'].iloc[0]))
    merged_df = pd.DataFrame(merged,
        columns=['index','Id работы','Фамилия','Имя','Кодовое слово','Орф. ошибки','Пункт. ошибки'])
    rest = df.drop(duplicates.index).copy()
    rest['index'] = rest.index
    rest = rest[['index','Id работы','Фамилия','Имя','Кодовое слово','Орф. ошибки','Пункт. ошибки']]
    return pd.concat([merged_df, rest], ignore_index=True).sort_values('index')

def normalize_and_explode(df, translit, nums):
    df = df.rename(columns={'Id работы':'id'}).reset_index(drop=True)
    for col in ['Фамилия','Имя','Кодовое слово']:
        df[col] = df[col].str.lower().str.split(',')
    df = df.explode(['Фамилия','Имя','Кодовое слово'])
    for mapping in (translit, nums):
        for k,v in mapping.items():
            df[['Фамилия','Имя','Кодовое слово']] = df[['Фамилия','Имя','Кодовое слово']].replace(k,v,regex=True)
    df[['Фамилия','Имя','Кодовое слово']] = df[['Фамилия','Имя','Кодовое слово']].replace('[^ёа-я]','',regex=True)
    df['ФИО'] = df['Фамилия'] + ' ' + df['Имя']
    df['Скан'] = df['id'].astype(str)+'.pdf'
    return df[['ФИО','Орф. ошибки','Пункт. ошибки','Кодовое слово','Скан']]

# --- Main ---
async def main():
    logger.info("Starting processing")
    sites = read_global_log(CONFIG['paths']['log_sheet_csv_url'])
    missing = []
    results = {}
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor()

    for site in sites:
        logger.info(f"Processing site {site}")
        try:
            # Simplified: load site-specific df chunk
            df = pd.read_csv(CONFIG['paths']['log_sheet_csv_url'], dtype={'№ площадки':str})
            df_site = df[df['№ площадки']==site]
            df_site = fill_missing_identifiers(df_site, CONFIG['codeword'])
            if check_missing_errors(df_site):
                missing.append(site)
                logger.warning(f"Missing grades for {site}")
                continue

            merged = merge_duplicate_pdfs(df_site, CONFIG['paths']['submissions_local'])
            final_df = normalize_and_explode(merged, TRANSLIT, NUMS)

            # Save & upload CSV
            csv_path = os.path.join(CONFIG['paths']['final_local'], f"{site}.csv")
            final_df.to_csv(csv_path, sep=';', encoding='cp1251', index=False)
            await async_upload(loop, executor, csv_path)

            # Save & upload ZIP
            zip_path = os.path.join(CONFIG['paths']['final_local'], f"{site}.zip")
            with ZipFile(zip_path, 'w') as zf:
                for fname in os.listdir(CONFIG['paths']['submissions_local']):
                    if fname.startswith(site):
                        zf.write(os.path.join(CONFIG['paths']['submissions_local'], fname), fname)
            await async_upload(loop, executor, zip_path)

            results[site] = final_df
            logger.info(f"Finished site {site}")
        except Exception as e:
            logger.error(f"Error processing {site}: {e}", exc_info=True)

    logger.info(f"Done. Missing grades for: {missing}")

TRANSLIT = {'a':'а','b':'б','c':'ц','d':'д','e':'е','f':'ф','g':'г','h':'х','i':'и','j':'й','k':'к','l':'л','m':'м','n':'н','o':'о','p':'п','r':'р','s':'с','t':'т','u':'у','v':'в','w':'вв','x':'кс','y':'ы','z':'з'}
NUMS = {'1':'один','2':'два','3':'три','4':'четыре','5':'пять','6':'шесть','7':'семь','8':'восемь','9':'девять','0':'ноль'}

if __name__ == "__main__":
    asyncio.run(main())
