from flask import Flask, request
from flasgger import Swagger
from flask_cors import CORS
import os
import logging
from datetime import datetime
from handlers_pdf import register_routes_pdf
from handlers_csv import register_routes_csv

app = Flask("Diploma")
CORS(app)
from flasgger import Swagger
swagger = Swagger(app)

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

register_routes_pdf(app)
register_routes_csv(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
