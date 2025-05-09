import pandas as pd
import os
from transliterate import translit

# Загрузка CSV
csv_path = 'part_1/all_files_final.csv'
df = pd.read_csv(csv_path, delimiter=',')

column_to_transliterate = df.columns[4]

df[column_to_transliterate] = df[column_to_transliterate].apply(
    lambda x: translit(str(x), 'ru', reversed=True) if isinstance(x, str) else x
)

df.to_csv('part_1/all_files_final.csv', index=False)

def transliterate_name(name):
    return translit(name, 'ru', reversed=True)

def rename_files_and_dirs(root_path):
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        # Переименование файлов
        for filename in filenames:
            new_filename = transliterate_name(filename)
            if new_filename != filename:
                src = os.path.join(dirpath, filename)
                dst = os.path.join(dirpath, new_filename)
                os.rename(src, dst)

        # Переименование поддиректорий
        for dirname in dirnames:
            old_dir = os.path.join(dirpath, dirname)
            new_dirname = transliterate_name(dirname)
            new_dir = os.path.join(dirpath, new_dirname)
            if new_dirname != dirname:
                os.rename(old_dir, new_dir)

# Пример использования
rename_files_and_dirs("part_1")
