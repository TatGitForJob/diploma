import os
import fitz  # PyMuPDF
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from PIL import Image
import io
import yadisk


# Авторизация
yandex = yadisk.YaDisk(token="y0__xDG74akqveAAhjblgMggf6o1xKS9mEBdAxviZ1aAoqtrPku2rA5qA")

def save_to_yandex_disk (save_folder, file_path):
    filename = os.path.basename(file_path)
    if not yandex.exists(save_folder):
        yandex.mkdir(save_folder)

    yandex.upload(file_path, f"{save_folder}/{filename}")
    print(f"Загружено: {filename}")

def crop_image_by_pixels(pixmap, crops):
    image = Image.open(io.BytesIO(pixmap.tobytes("png")))
    width, height = image.size
    parts = []
    for top, bottom in crops:
        cropped = image.crop((0, top, width, bottom))
        buf = io.BytesIO()
        cropped.save(buf, format='PNG')
        parts.append(buf)
    return parts

def process_pdf(pdf_path, crops):
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return [None, None, None]

    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    return crop_image_by_pixels(pix, crops)

def insert_images_to_excel(pdf_folder, output_excel):
    wb = Workbook()
    ws = wb.active

    row = 1
    for filename in os.listdir(pdf_folder):
        if not filename.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(pdf_folder, filename)
        print(f"Обработка: {filename}")

        save_to_yandex_disk("/12345",pdf_path)

        # Укажи здесь crop'ы по пикселям (top, bottom)
        crops = [
            (0, 400),      # верхняя часть
            (400, 800),    # средняя часть
            (800, 1200),   # нижняя часть
        ]

        images = process_pdf(pdf_path, crops)
        max_height_px = 0  # Для определения максимальной высоты строки

        col=1
        cell = ws.cell(row=row, column=1)
        print(os.path.splitext(filename)[0]+"_"+str(row))

        for _, img_buf in enumerate(images, start=1):
            if img_buf:
                col+=1
                img = XLImage(img_buf)
                pil_img = Image.open(img_buf)
                width_px, height_px = pil_img.size

                # Добавление изображения
                cell = ws.cell(row=row, column=col)
                ws.add_image(img, cell.coordinate)

                # Автоустановка ширины столбца (примерно: 1 символ ≈ 7 пикселей)
                col_letter = cell.column_letter
                ws.column_dimensions[col_letter].width = width_px / 7

                # Обновление высоты строки
                if height_px > max_height_px:
                    max_height_px = height_px

        # Автоустановка высоты столбца (примерно: 1 поинт ≈ 0.75 пикселя)
        ws.row_dimensions[row].height = max_height_px * 0.75

        row += 1

    wb.save(output_excel)
    print(f"✅ Сохранено в: {output_excel}")

# Настрой путь и имя файла
pdf_folder = "../pdfs"  # Папка с PDF-файлами
output_excel = "out.xlsx"
insert_images_to_excel(pdf_folder, output_excel)
