import { useState, useEffect } from "react";
import axios from "axios";

const validCities = {
  Moscow: "mos123",
  Piter: "pit456",
  Novgorod: "nov789",
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
    <div className="min-h-screen bg-gradient-to-r from-gray-100 to-blue-100 flex flex-col items-center justify-center p-6 font-sans">
      {step === 1 && (
        <div className="bg-white shadow-xl rounded-lg p-8 w-full max-w-md space-y-5">
          <h1 className="text-3xl font-bold text-center text-gray-800">Вход</h1>
          <input
            type="text"
            placeholder="Город (Moscow, Piter, Novgorod)"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full border px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            onClick={handleLogin}
            className="w-full bg-blue-600 text-white py-3 text-lg rounded-md hover:bg-blue-700 transition"
          >
            Войти
          </button>
          {message && <p className="text-red-600 text-sm text-center">{message}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-6 text-center w-full max-w-6xl">
          <h2 className="text-2xl font-semibold text-gray-700">🏙️ Город: {city}</h2>
          <div className="flex flex-wrap gap-4 justify-center">
            <button
              onClick={handleProcess}
              disabled={loading}
              className="bg-green-600 text-white px-6 py-3 rounded-md text-lg hover:bg-green-700 disabled:opacity-60"
            >
              {loading ? "Обработка..." : "Запустить обработку"}
            </button>
            <button
              onClick={handleFetchXlsxFiles}
              className="bg-blue-500 text-white px-6 py-3 rounded-md text-lg hover:bg-blue-600"
            >
              Список Excel-файлов
            </button>
            <button
              onClick={handleDownloadSelected}
              className="bg-purple-500 text-white px-6 py-3 rounded-md text-lg hover:bg-purple-600"
            >
              Скачать выбранные
            </button>
            <button
              onClick={handleLogout}
              className="bg-red-500 text-white px-6 py-3 rounded-md text-lg hover:bg-red-600"
            >
              Выйти
            </button>
          </div>
          {message && <p className="text-blue-700 font-medium">{message}</p>}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
            {processedFiles.length > 0 && (
              <FileList title="Обработанные" color="green" files={processedFiles} />
            )}
            {duplicateFiles.length > 0 && (
              <FileList title="Дубликаты" color="yellow" files={duplicateFiles} />
            )}
            {xlsxFiles.length > 0 && (
                <div>
                    <h3 className="font-semibold text-lg text-indigo-700 mb-2">Файлы Excel</h3>
                    <ul className="text-sm text-left bg-white rounded-md shadow p-3 w-64">
                        {xlsxFiles.map((file, i) => (
                            <li
                                key={i}
                                className={`cursor-pointer px-2 py-1 my-1 rounded border text-sm transition-colors ${
                                    selectedFiles.includes(file)
                                        ? 'bg-indigo-100 border-indigo-500 text-indigo-800 font-semibold'
                                        : 'border-gray-300 hover:bg-indigo-50 text-gray-800'
                                }`}
                                onClick={() => handleFileToggle(file)}
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

function FileList({ title, files, color, selectable = false, selectedFiles = [], onToggle }) {
  return (
    <div>
      <h3 className={`font-semibold text-lg text-${color}-700 mb-3`}>{title}</h3>
      <ul className="list-none space-y-2 text-sm text-left bg-white rounded-md shadow p-3 w-64">
        {files.map((file, i) => (
          <li
            key={i}
            className={`px-3 py-2 rounded border cursor-pointer text-sm ${
              selectable
                ? selectedFiles.includes(file)
                  ? `bg-${color}-100 border-${color}-400 text-${color}-800 font-semibold`
                  : `hover:bg-${color}-50 border-gray-300`
                : "border-gray-200"
            }`}
            onClick={selectable ? () => onToggle(file) : undefined}
          >
            {file}
          </li>
        ))}
      </ul>
    </div>
  );
}
