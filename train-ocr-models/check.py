import pandas as pd
import os

# Путь к CSV
csv_path = 'part_1/all_files_final.csv'

# Загрузка CSV
df = pd.read_csv(csv_path)

# Столбец с путями к файлам
path_column = 'new_path'  # Замени на свой, если у тебя другое имя

# Счётчики
missing_files = []

for path in df[path_column]:
    if not os.path.isfile(path):
        missing_files.append(path)

# Вывод результатов
if missing_files:
    print(f"❌ Найдено {len(missing_files)} отсутствующих файлов:")
    for path in missing_files:
        print("   -", path)
else:
    print("✅ Все файлы на месте!")
