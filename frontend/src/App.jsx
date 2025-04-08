import { useState, useEffect } from "react";
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
    setMessage("⏳ Обработка запущена...");
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
            <button onClick={handleProcess} disabled={loading} className="btn">
              {loading ? "Обработка..." : "Запустить обработку"}
            </button>
            <button onClick={handleFetchXlsxFiles} className="btn">
              Список Excel-файлов
            </button>
            <button onClick={handleDownloadSelected} className="btn">
              Скачать выбранные
            </button>
            <button onClick={handleLogout} className="btn danger">
              Выйти
            </button>
          </div>

          {message && <p className="info-message">{message}</p>}

          <div className="file-columns">
            {processedFiles.length > 0 && (
              <FileList title="Обработанные" files={processedFiles} className="green-title" />
            )}
            {duplicateFiles.length > 0 && (
              <FileList title="Дубликаты" files={duplicateFiles} className="brown-title" />
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

function FileList({ title, files, className }) {
  return (
    <div>
      <h3 className={className}>{title}</h3>
      <ul className="file-list">
        {files.map((file, i) => (
          <li key={i} className="file-item">{file}</li>
        ))}
      </ul>
    </div>
  );
}
