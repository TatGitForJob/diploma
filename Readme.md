# 📂 PDF Processor + Yandex Disk + Excel Автоматизация

Этот проект автоматически:

- Загружает PDF-файлы с Яндекс.Диска
- Разбивает их на части
- Извлекает изображения
- Создаёт Excel-отчёт с картинками и публичными ссылками
- Загружает результат обратно на Яндекс.Диск

---

## 🚀 Быстрый старт

### 📦 Установка

```bash
git clone https://github.com/TatGitForJob/diploma.git
cd diploma
python -m venv venv
source venv/bin/activate
source backend/setup.py
apt install npm
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install axios
npm run dev
```

---

### ⚙️ Настройка `.env`

Создай файл `.env` в корне проекта и добавь туда:

```dotenv
YANDEX_TOKEN=ваш_токен_из_https://yandex.ru/dev/disk/poligon/
```

> 🛡️ Не публикуй `.env` в репозитории — он содержит приватный доступ к Яндекс.Диску!

---

### 📂 Структура проекта

```
.
├── main.py                 # Точка входа: обработка всех PDF-файлов
├── pdf_processor.py        # Асинхронная обработка одного PDF
├── excel_filler.py         # Заполнение Excel с картинками и ссылками
├── .env                    # Хранит YANDEX_TOKEN (вне git)
└── README.md               # Документация проекта
```

---

### 🏁 Запуск

Укажи название города (папки на Яндекс.Диске) как аргумент командной строки:

```bash
python3 main.py Moscow
```

Поддерживаемые города:

- Moscow
- Piter
- Novgorod

Каждый PDF-файл внутри `/Moscow`, `/Piter` и т.д. будет обработан независимо.

---

## ⚙️ Что делает `main.py`

1. Ищет PDF-файлы в папке `/Город` на Яндекс.Диске
2. Проверяет дубликаты и создаёт временные локальные папки
3. Загружает PDF, разбивает на части
4. Извлекает изображения и вставляет в Excel-таблицу
5. Добавляет в таблицу публичную ссылку на исходный PDF
6. Загружает готовую Excel обратно на Яндекс.Диск
7. Перемещает обработанный файл в `/Город/done`

---

## ✅ Зависимости

Устанавливаются через `requirements.txt`, включают:

- `python-dotenv` — загрузка `.env`
- `openpyxl` — работа с Excel
- `PyMuPDF` — извлечение страниц из PDF
- `Pillow` — работа с изображениями
- `yadisk` — API для Яндекс.Диска
- `PyPDF2` — разбивка PDF

---

## 🛑 Важно

- Убедись, что у тебя есть активный токен в `.env`
- Файлы Excel и PDF загружаются в подпапки вроде `/Moscow_pdf`, `/Moscow_xlsx`
- Используются **все ядра процессора** для параллельной обработки PDF

---

## 📬 Обратная связь

Если возникли вопросы или предложения — пиши в Issues или Telegram [@bibop\_bibop].
