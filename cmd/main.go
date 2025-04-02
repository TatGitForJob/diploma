package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/xuri/excelize/v2"
)

func slicePDFIntoThreeParts(pdfPath, outputDir string) ([]string, error) {
	baseName := strings.TrimSuffix(filepath.Base(pdfPath), ".pdf")
	tempDir := filepath.Join(outputDir, baseName)
	err := os.MkdirAll(tempDir, os.ModePerm)
	if err != nil {
		return nil, err
	}

	// 1. PDF → JPG (по одной странице)
	imgPrefix := filepath.Join(tempDir, "page")
	cmd1 := exec.Command("pdftoppm", "-jpeg", "-r", "300", pdfPath, imgPrefix)
	if out, err := cmd1.CombinedOutput(); err != nil {
		return nil, fmt.Errorf("pdftoppm error: %v, output: %s", err, string(out))
	}

	// 2. Найдём сгенерированные jpg
	jpgs, err := filepath.Glob(filepath.Join(tempDir, "page-*.jpg"))
	if err != nil || len(jpgs) == 0 {
		return nil, fmt.Errorf("no JPGs found after pdftoppm")
	}

	partPDFs := []string{}

	for i, img := range jpgs {
		for j := 0; j < 3; j++ {
			// 3. Нарезка: crop изображение на 3 вертикальные части
			croppedImg := filepath.Join(tempDir, fmt.Sprintf("page%02d_part%d.jpg", i+1, j+1))
			geometry := fmt.Sprintf("x33%%+0+%d%%", j*33)
			cmdCrop := exec.Command("convert", img, "-crop", geometry, "+repage", croppedImg)
			if out, err := cmdCrop.CombinedOutput(); err != nil {
				return nil, fmt.Errorf("crop error: %v, output: %s", err, string(out))
			}

			// 4. JPEG → PDF
			partPDF := filepath.Join(outputDir, fmt.Sprintf("%s_p%02d_part%d.pdf", baseName, i+1, j+1))
			cmdToPDF := exec.Command("convert", croppedImg, partPDF)
			if out, err := cmdToPDF.CombinedOutput(); err != nil {
				return nil, fmt.Errorf("convert to PDF error: %v, output: %s", err, string(out))
			}
			partPDFs = append(partPDFs, partPDF)
		}
	}

	return partPDFs, nil
}

func processPDFDirectory(pdfDir, xlsPath string) error {
	// Создаем/открываем файл Excel
	f := excelize.NewFile()
	sheet := "Sheet1"
	index, err := f.NewSheet(sheet)
	if err != nil {
		return err
	}

	// Поиск всех PDF файлов в папке
	files, err := filepath.Glob(filepath.Join(pdfDir, "*.pdf"))
	if err != nil {
		return err
	}

	row := 1
	for _, pdfPath := range files {
		parts, err := slicePDFIntoThreeParts(pdfPath, "out")
		if err != nil {
			log.Printf("Ошибка при нарезке %s: %v\n", pdfPath, err)
			continue
		}

		// Добавляем 3 части в строку
		for i, part := range parts {
			cell, _ := excelize.CoordinatesToCellName(i+1, row)
			f.SetCellValue(sheet, cell, filepath.Base(part)) // или `part`, если нужен полный путь
		}
		row++
	}

	f.SetActiveSheet(index)
	return f.SaveAs(xlsPath)
}

func main() {
	if len(os.Args) < 3 {
		log.Fatal("Использование: go run main.go <pdf_dir> <output.xlsx>")
	}

	pdfDir := os.Args[1]
	xlsPath := os.Args[2]

	err := processPDFDirectory(pdfDir, xlsPath)
	if err != nil {
		log.Fatalf("Ошибка обработки: %v", err)
	}

	fmt.Println("Готово!")
}
