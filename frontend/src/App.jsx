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
  const [xlsxFiles, setXlsxFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [processedFiles, setProcessedFiles] = useState([]);
  const [duplicateFiles, setDuplicateFiles] = useState([]);
  const [uploadedPdfs, setUploadedPdfs] = useState([]);
  const [failedPdfs, setFailedPdfs] = useState([]);
  const fileInputRef = useRef(null);

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
    setXlsxFiles([]);
    setSelectedFiles([]);
    setProcessedFiles([]);
    setDuplicateFiles([]);
  };

  const handleProcess = async () => {
    setLoading(true);
    setMessage("⏳ Обработка PDF запущена...");
    setProcessedFiles([]);
    setDuplicateFiles([]);
    try {
      const res = await axios.post("http://localhost:8000/process", { sity: city });
      const data = res.data || {};
      if (typeof data === "object") {
        setMessage(data.status || "✅ Готово");
        setProcessedFiles(Array.isArray(data.processed) ? data.processed : []);
        setDuplicateFiles(Array.isArray(data.duplicates) ? data.duplicates : []);
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
    setUploadedPdfs([]);
    setFailedPdfs([]);
    setProcessedFiles([]);
    setDuplicateFiles([]);
    setXlsxFiles([]);
    setSelectedFiles([]);
    try {
      const res = await axios.get("http://localhost:8000/xlsx-list", {
        params: { sity: city },
      });
      setXlsxFiles(res.data.files || []);
      setMessage(`📄 Найдено файлов: ${res.data.files.length}`);
    } catch (err) {
      setMessage("❌ Ошибка при получении списка файлов");
    }
  };

  const handleFileToggle = (filename) => {
    setSelectedFiles((prev) =>
      prev.includes(filename) ? prev.filter((f) => f !== filename) : [...prev, filename]
    );
  };

  const handleDownloadSelected = async () => {
    setSelectedFiles([]);
    if (selectedFiles.length === 0) {
      setMessage("⚠️ Сначала выберите файлы");
      return;
    }
    try {
      setMessage("📦 Запрос на скачивание отправлен...");
      const response = await axios.post(
        "http://localhost:8000/download-xlsx",
        {
          sity: city,
          files: selectedFiles,
        },
        { responseType: "blob" }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${city}_selected_files.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();

      setMessage("✅ Архив получен и загружен");
    } catch (err) {
      setMessage("❌ Ошибка при скачивании файлов");
    }
  };

  const handlePdfUpload = async (event) => {
    setUploadedPdfs([]);
    setFailedPdfs([]);
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const formData = new FormData();
    formData.append("sity", city);
    for (let file of files) {
      formData.append("files", file);
    }

    try {
      setMessage("📤 Загрузка PDF-файлов...");
      const res = await axios.post("http://localhost:8000/upload-pdf", formData);
      const data = res.data;
      const uploaded = data.uploaded || [];
      const failed = data.failed || [];

      setUploadedPdfs(uploaded);
      setFailedPdfs(failed);
      setMessage(`✅ Загружено: ${uploaded.length}, ❌ Ошибки: ${failed.length}`);
    } catch (err) {
      console.error(err);
      setMessage("❌ Ошибка при загрузке PDF-файлов");
    }

    event.target.value = null;
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
            <button onClick={() => fileInputRef.current.click()} className="btn">
              Загрузить PDF
            </button>
            <input
              type="file"
              accept="application/pdf"
              multiple
              style={{ display: "none" }}
              ref={fileInputRef}
              onChange={handlePdfUpload}
            />
            <button onClick={handleProcess} disabled={loading} className="btn">
              {loading ? "Обработка..." : "Запустить обработку"}
            </button>
            <button onClick={handleFetchXlsxFiles} className="btn">
              Список Excel-файлов
            </button>
            <button onClick={handleDownloadSelected} className="btn">
              Скачать Excel
            </button>
            <button onClick={handleLogout} className="btn danger">
              Выйти
            </button>
          </div>

          {message && <p className="info-message">{message}</p>}

          <div className="file-columns">
            {uploadedPdfs.length > 0 && (
              <FileList title="Загруженные PDF" files={uploadedPdfs} className="green-title" clickable={false} />
            )}
            {failedPdfs.length > 0 && (
              <FileList title="Не загруженные PDF" files={failedPdfs} className="brown-title" clickable={false} />
            )}
            {processedFiles.length > 0 && (
              <FileList title="Обработанные PDF" files={processedFiles} className="green-title" clickable={false} />
            )}
            {duplicateFiles.length > 0 && (
              <FileList title="Дубликаты PDF" files={duplicateFiles} className="brown-title" clickable={false} />
            )}
            {xlsxFiles.length > 0 && (
              <div>
                <h3 className="blue-title">Файлы Excel</h3>
                <ul className="file-list">
                  {xlsxFiles.map((file, i) => (
                    <li
                      key={i}
                      onClick={() => handleFileToggle(file)}
                      className={`file-item ${selectedFiles.includes(file) ? "selected" : ""}`}
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
