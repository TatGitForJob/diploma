# DictaCore

Клиент-серверное приложение для обработки бланков проекта «Тотальный диктант». Приложение принимает PDF-файлы через веб-интерфейс, извлекает данные с помощью OCR и ML-модели, формирует Excel-файлы для ручной проверки и затем преобразует проверенные файлы в итоговые CSV.

## Возможности

- загрузка PDF-файлов через веб-интерфейс
- извлечение изображений и данных из PDF
- распознавание данных с помощью модели на базе `transformers`
- формирование Excel-файлов для ручной проверки
- загрузка проверенных Excel-файлов
- генерация итоговых CSV-файлов
- работа с файлами через Яндекс.Диск

## Требования

- Docker
- `docker-compose`

Проверка доступности инструментов:

```bash
docker --version
docker-compose version
```

## Настройка

Конфигурация находится в файле `backend/auth.py`.

В этом файле задаются:

- список городов
- пароли для входа
- кодовые слова
- токен Яндекс.Диска

Пример значения токена:

```python
YANDEX_TOKEN = "ваш_токен_из_https://yandex.ru/dev/disk/poligon"
```

## Модель

Для работы backend требуется каталог `backend/vit-base-letters_2/` с файлами модели. В репозитории этот каталог уже присутствует. Если модель нужно заменить или восстановить, используйте совместимый набор файлов модели для текущей реализации OCR.

## Запуск

Клонирование репозитория:

```bash
git clone https://github.com/TatGitForJob/diploma.git
cd diploma
```

Сборка и запуск:

```bash
docker-compose up --build -d
```

Проверка состояния контейнеров:

```bash
docker-compose ps
```

Остановка приложения:

```bash
docker-compose down
```

Адреса сервисов после запуска:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8080`

## Использование

1. Откройте `http://localhost:5173`.
2. Войдите под одним из городов, заданных в `backend/auth.py`.
3. Загрузите PDF-файлы.
4. Запустите обработку PDF.
5. Скачайте сформированные Excel-файлы.
6. После ручной проверки загрузите Excel-файлы обратно.
7. Запустите обработку Excel и скачайте итоговые CSV-файлы.

## Структура проекта

```text
project-root/
├── backend/
│   ├── auth.py
│   ├── main.py
│   ├── ocr.py
│   ├── pdf_processor.py
│   └── vit-base-letters_2/
├── docker-compose.yml
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── train-final-model/
└── train-ocr-models/
```

## Полезные команды

Просмотр логов:

```bash
docker-compose logs -f
```

Пересборка без использования старых контейнеров:

```bash
docker-compose down
docker-compose up --build -d
```

Проверка frontend-сборки локально:

```bash
cd frontend
npm install
npm run build
```
