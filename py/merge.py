import os
from PyPDF2 import PdfMerger  # PyPDF2 >= 2.0

def merge_pdfs_from_folder(input_folder, output_path):
    merger = PdfMerger()

    pdf_files = sorted([
        f for f in os.listdir(input_folder)
        if f.lower().endswith('.pdf')
    ])

    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_folder, pdf_file)
        print(f"Добавляется: {pdf_file}")
        merger.append(pdf_path)

    merger.write(output_path)
    merger.close()
    print(f"✅ Объединённый файл сохранён как: {output_path}")

# Укажи свою папку и имя итогового файла
pdf_folder = "./pdfs"  # Папка с PDF-файлами
output_pdf = "merged_result.pdf"

merge_pdfs_from_folder(pdf_folder,output_pdf)