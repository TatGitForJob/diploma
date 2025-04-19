#!/bin/bash

# Проверка наличия python3
if ! command -v python3 &> /dev/null; then
    echo "python3 не найден. Пожалуйста, установите Python 3."
    exit 1
fi

sudo apt-get update
sudo apt-get install python3-venv



source venv/bin/activate
cd backend
source .env
nohup python3 main.py > log.txt 2>&1
localhost:8080/apidocs/



# Создание виртуального окружения, если оно отсутствует
if [ ! -d "venv" ]; then
    echo "Создаётся виртуальное окружение..."
    python3 -m venv venv
fi

# Определение пути до скрипта активации виртуального окружения
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "script activating virt env not found in venv/bin/activate"
    exit 1
fi

source ../.env

python -m ensurepip --upgrade
pip install --upgrade pip
# Установка необходимых библиотек
pip install PyMuPDF openpyxl pillow PyPDF2 yadisk requests flask flask_cors

echo "Настройка завершена! Для активации окружения в будущем выполните: source $ACTIVATE_SCRIPT"

python3 main.py

localhost:8000/apidocs/