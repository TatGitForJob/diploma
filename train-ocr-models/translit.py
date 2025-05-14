import pandas as pd
import os
from transliterate import translit

def safe_translit(text):
    custom = {
        'э': 'eh',
        'ё': 'eu'
    }
    text = ''.join(custom.get(c, c) for c in text)
    return translit(text, 'ru', reversed=True)

csv_path = 'part_1/all_files_final.csv'
df = pd.read_csv(csv_path, delimiter=',')

column_to_transliterate = df.columns[1]

df[column_to_transliterate] = df[column_to_transliterate].apply(
    lambda x: safe_translit(str(x)) if isinstance(x, str) else x
)

df.to_csv('part_1/all_files_final.csv', index=False)


def rename_files_and_dirs(root_path):
    for dirpath, dirnames, filenames in os.walk(root_path, topdown=False):
        for filename in filenames:
            new_filename = safe_translit(filename)
            if new_filename != filename:
                src = os.path.join(dirpath, filename)
                dst = os.path.join(dirpath, new_filename)
                os.rename(src, dst)

        for dirname in dirnames:
            old_dir = os.path.join(dirpath, dirname)
            new_dirname = safe_translit(dirname)
            new_dir = os.path.join(dirpath, new_dirname)
            if new_dirname != dirname:
                os.rename(old_dir, new_dir)

rename_files_and_dirs("part_1")
