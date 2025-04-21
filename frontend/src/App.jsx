import { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./index.css";

const validCities = {
  Moscow: "mos123",
  Novosibirsk: "nov456",
};

export default function CityApp() {
  const [step, setStep] = useState(1);
  const [city, setCity] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const pdfInputRef = useRef(null);
  const [uploadedPdf, setUploadedPdf] = useState([]);
  const [failedUploadedPdf, setFailedUploadedPdf] = useState([]);

  const [processedPdf, setProcessedPdf] = useState([]);
  const [duplicatePdf, setDuplicatePdf] = useState([]);
  const [failedPdf, setFailedPdf] = useState([]);

  const [xlsxFiles, setXlsxFiles] = useState([]);
  const [selectedXlsx, setSelectedXlsx] = useState([]);


  const excelInputRef = useRef(null);
  const [uploadedXlsx, setUploadedXlsx] = useState([]);
  const [failedUploadedXlsx, setFailedUploadedXlsx] = useState([]);

  const [processedCsv, setProcessedCsv] = useState([]);
  const [duplicateCsv, setDuplicateCsv] = useState([]);
  const [failedCsv, setFailedCsv] = useState([]);
  
  const [csvFiles, setCsvFiles] = useState([]);
  const [selectedCsv, setSelectedCsv] = useState([]);

  const resetAll = () => {
    setUploadedPdf([]);
    setFailedUploadedPdf([]);
    setProcessedPdf([]);
    setDuplicatePdf([]);
    setFailedPdf([]);
    setXlsxFiles([]);
    setSelectedXlsx([]);
    setUploadedXlsx([]);
    setFailedUploadedXlsx([]);
    setProcessedCsv([]);
    setDuplicateCsv([]);
    setFailedCsv([]);
    setCsvFiles([]);
    setSelectedCsv([]);
  };

  useEffect(() => {
    const storedCity = localStorage.getItem("authCity");
    if (storedCity && validCities[storedCity]) {
      setCity(storedCity);
      setStep(2);
    }
  }, []);

  const handleLogin = () => {
    if (validCities[city] && validCities[city] === password) {
      localStorage.setItem("authCity", city);
      setStep(2);
      setMessage("");
    } else {
      setMessage("❌ Неверный город или пароль");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("authCity");
    setCity("");
    setPassword("");
    setStep(1);
    setMessage("");
    resetAll()
  };
  const handlePdfUpload = async (event) => {
    resetAll()
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    formData.append("sity", city);
    for (let file of files) {
      formData.append("files", file);
    }

    try {
      setMessage("📤 Загрузка PDF-файлов...");
      const res = await axios.post("http://51.250.8.183:8080/upload-pdf", formData);
      const data = res.data;
      const uploaded = data.uploaded || [];
      const failed = data.failed || [];

      setUploadedPdf(uploaded);
      setFailedUploadedPdf(failed);
      setMessage(`✅ Загружено: ${uploaded.length}, ❌ Ошибки: ${failed.length}`);
    } catch (err) {
      console.error(err);
      setMessage("❌ Ошибка при загрузке PDF-файлов");
    }

    event.target.value = null;
  };
  const handleExcelUpload = async (event) => {
    resetAll();
    const files = event.target.files;
    if (!files || files.length === 0) return;
  
    const formData = new FormData();
    formData.append("sity", city);
    for (let file of files) {
      formData.append("files", file);
    }
  
    try {
      setMessage("📤 Загрузка Excel-файлов...");
      const res = await axios.post("http://51.250.8.183:8080/upload-excel", formData);
      const data = res.data;
      const uploaded = data.uploaded || [];
      const failed = data.failed || [];
  
      setUploadedXlsx(uploaded);
      setFailedUploadedXlsx(failed);
      setMessage(`✅ Загружено: ${uploaded.length}, ❌ Ошибки: ${failed.length}`);
    } catch (err) {
      console.error(err);
      setMessage("❌ Ошибка при загрузке Excel-файлов");
    }
  
    event.target.value = null;
  };  
  const handleProcessPdf = async () => {
    setLoading(true);
    setMessage("⏳ Обработка PDF запущена...");
    resetAll()
    try {
      const res = await axios.post("http://51.250.8.183:8080/process-pdf", { sity: city });
      const data = res.data || {};
      if (typeof data === "object") {
        setMessage(data.status || "✅ Готово");
        setProcessedPdf(Array.isArray(data.processed) ? data.processed : []);
        setDuplicatePdf(Array.isArray(data.duplicates) ? data.duplicates : []);
        setFailedPdf(Array.isArray(data.failed) ? data.failed.map(f => `${f.name}: ${f.error}`) : []);
      } else {
        setMessage("⚠️ Некорректный ответ от сервера");
      }
    } catch (err) {
      console.error(err);
      setMessage("❌ Ошибка при запуске обработки");
    }
    setLoading(false);
  };
  const handleProcessExcel = async () => {
    setLoading(true);
    setMessage("⏳ Обработка Excel запущена...");
    resetAll()
    try {
      const res = await axios.post("http://51.250.8.183:8080/process-excel", { sity: city });
      const data = res.data || {};
      if (typeof data === "object") {
        setMessage(data.status || "✅ Готово");
        setProcessedCsv(Array.isArray(data.processed) ? data.processed : []);
        setDuplicateCsv(Array.isArray(data.duplicates) ? data.duplicates : []);
        setFailedCsv(Array.isArray(data.failed) ? data.failed.map(f => `${f.name}: ${f.error}`) : []);
      } else {
        setMessage("⚠️ Некорректный ответ от сервера");
      }
    } catch (err) {
      console.error(err);
      setMessage("❌ Ошибка при запуске обработки");
    }
    setLoading(false);
  };
  const handleFetchXlsxFiles = async () => {
    setMessage("⏳ Поиск Excel запущен...");
    resetAll()
    try {
      const res = await axios.get("http://51.250.8.183:8080/xlsx-list", {
        params: { sity: city },
      });
      setXlsxFiles(res.data.files || []);
      setMessage(`📄 Найдено файлов: ${res.data.files.length}`);
    } catch (err) {
      setMessage("❌ Ошибка при получении списка файлов");
    }
  };
  const handleFetchCsvFiles = async () => {
    setMessage("⏳ Поиск обработанных работ запущен...");
    resetAll()
    try {
      const res = await axios.get("http://51.250.8.183:8080/csv-list", {
        params: { sity: city },
      });
      setCsvFiles(res.data.files || []);
      setMessage(`📄 Найдено файлов: ${res.data.files.length}`);
    } catch (err) {
      setMessage("❌ Ошибка при получении списка файлов");
    }
  };
  const handleXlsxToggle = (filename) => {
    setSelectedXlsx((prev) =>
      prev.includes(filename) ? prev.filter((f) => f !== filename) : [...prev, filename]
    );
  };
  const handleCsvToggle = (filename) => {
    setSelectedCsv((prev) =>
      prev.includes(filename) ? prev.filter((f) => f !== filename) : [...prev, filename]
    );
  };
  const handleDownloadXlsx = async () => {
    resetAll()
    if (selectedXlsx.length === 0) {
      setMessage("⚠️ Сначала выберите файлы");
      return;
    }
    try {
      setMessage("📦 Запрос на скачивание отправлен...");
      const response = await axios.post(
        "http://51.250.8.183:8080/download-xlsx",
        {
          sity: city,
          files: selectedXlsx,
        },
        { responseType: "blob" }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${city}_selected_xlsx.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      setMessage("✅ Архив получен и загружен");
    } catch (err) {
      setMessage("❌ Ошибка при скачивании файлов");
    }
  };
  const handleDownloadCsv = async () => {
    resetAll()
    if (selectedCsv.length === 0) {
      setMessage("⚠️ Сначала выберите файлы");
      return;
    }
    try {
      setMessage("📦 Запрос на скачивание отправлен...");
      const response = await axios.post(
        "http://51.250.8.183:8080/download-csv",
        {
          sity: city,
          files: selectedCsv,
        },
        { responseType: "blob" }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${city}_selected_csv.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      setMessage("✅ Архив получен и загружен");
    } catch (err) {
      setMessage("❌ Ошибка при скачивании файлов");
    }
  };
  return (
    <div className="page">
      {step === 1 && (
        <div className="card">
          <h1 className="title">Вход по городу</h1>

          <label>Город</label>
          <input
            type="text"
            placeholder="Город (Moscow, Novosibirsk)"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />

          <label>Пароль</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <button onClick={handleLogin} className="btn main-btn">
            Войти
          </button>

          {message && <p className="error-message">{message}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="dashboard">
          <h2 className="subtitle">🏙️ Город: {city}</h2>

          <div className="button-group">
            <button onClick={() => pdfInputRef.current.click()} className="btn">
              Загрузить PDF
            </button>
            <input
              type="file"
              accept="application/pdf"
              multiple
              style={{ display: "none" }}
              ref={pdfInputRef}
              onChange={handlePdfUpload}
            />
            <button onClick={handleProcessPdf} disabled={loading} className="btn">
              {loading ? "Обработка..." : "Запустить предобработку"}
            </button>
            <button onClick={handleFetchXlsxFiles} className="btn">
              Список Excel-файлов
            </button>
            <button onClick={handleDownloadXlsx} className="btn">
              Скачать Excel
            </button>
            <button onClick={() => excelInputRef.current.click()} className="btn">
              Загрузить проверенный Excel
            </button>
            <input
              type="file"
              accept=".xlsx"
              multiple
              style={{ display: "none" }}
              ref={excelInputRef}
              onChange={handleExcelUpload}
            />
            <button onClick={handleProcessExcel} disabled={loading} className="btn">
              {loading ? "Обработка..." : "Запустить постобработку"}
            </button>
            <button onClick={handleFetchCsvFiles} className="btn">
              Список Csv-файлов
            </button>
            <button onClick={handleDownloadCsv} className="btn">
              Скачать Csv
            </button>
            <button onClick={handleLogout} className="btn danger">
              Выйти
            </button>
          </div>

          {message && <p className="info-message">{message}</p>}

          <div className="file-columns">
            {uploadedPdf.length > 0 && (
              <FileList title="Загруженные PDF" files={uploadedPdf} className="green-title" clickable={false} />
            )}
            {failedUploadedPdf.length > 0 && (
              <FileList title="Не загруженные PDF" files={failedUploadedPdf} className="brown-title" clickable={false} />
            )}
            {processedPdf.length > 0 && (
              <FileList title="Обработанные PDF" files={processedPdf} className="green-title" clickable={false} />
            )}
            {duplicatePdf.length > 0 && (
              <FileList title="Дубликаты PDF" files={duplicatePdf} className="brown-title" clickable={false} />
            )}
            {failedPdf.length > 0 && (
              <FileList title="Ошибки обработки PDF" files={failedPdf} className="red-title" clickable={false} />
            )}
            {xlsxFiles.length > 0 && (
              <div>
                <h3 className="blue-title">Файлы Excel</h3>
                <ul className="file-list">
                  {xlsxFiles.map((file, i) => (
                    <li
                      key={i}
                      onClick={() => handleXlsxToggle(file)}
                      className={`file-item ${selectedXlsx.includes(file) ? "selected" : ""}`}
                    >
                      {file}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {uploadedXlsx.length > 0 && (
              <FileList title="Загруженные Excel" files={uploadedXlsx} className="green-title" clickable={false} />
            )}
            {failedUploadedXlsx.length > 0 && (
              <FileList title="Не загруженные Excel" files={failedUploadedXlsx} className="brown-title" clickable={false} />
            )}
            {processedCsv.length > 0 && (
              <FileList title="Обработанные Excel" files={processedCsv} className="green-title" clickable={false} />
            )}
            {duplicateCsv.length > 0 && (
              <FileList title="Дубликаты Excel" files={duplicateCsv} className="brown-title" clickable={false} />
            )}
            {failedCsv.length > 0 && (
              <FileList title="Ошибки обработки Excel" files={failedCsv} className="red-title" clickable={false} />
            )}
            {csvFiles.length > 0 && (
              <div>
                <h3 className="blue-title">Файлы Csv</h3>
                <ul className="file-list">
                  {csvFiles.map((file, i) => (
                    <li
                      key={i}
                      onClick={() => handleCsvToggle(file)}
                      className={`file-item ${selectedCsv.includes(file) ? "selected" : ""}`}
                    >
                      {file}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function FileList({ title, files, className, clickable = false }) {
  return (
    <div>
      <h3 className={className}>{title}</h3>
      <ul className="file-list">
        {files.map((file, i) => (
          <li key={i} className={`file-item ${!clickable ? "non-clickable" : ""}`}>{file}</li>
        ))}
      </ul>
    </div>
  );
}
