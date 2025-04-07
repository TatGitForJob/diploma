import { useState, useEffect } from "react"
import axios from "axios"

const validCities = {
  Moscow: "mos123",
  Piter: "pit456",
  Novgorod: "nov789",
}

export default function CityApp() {
  const [step, setStep] = useState(1)
  const [city, setCity] = useState("")
  const [password, setPassword] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [xlsxFiles, setXlsxFiles] = useState([])
  const [processedFiles, setProcessedFiles] = useState([])
  const [duplicateFiles, setDuplicateFiles] = useState([])

  useEffect(() => {
    const storedCity = localStorage.getItem("authCity")
    if (storedCity && validCities[storedCity]) {
      setCity(storedCity)
      setStep(2)
    }
  }, [])

  const handleLogin = () => {
    if (validCities[city] && validCities[city] === password) {
      localStorage.setItem("authCity", city)
      setStep(2)
      setMessage("")
    } else {
      setMessage("Неверный город или пароль")
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("authCity")
    setCity("")
    setPassword("")
    setStep(1)
    setMessage("")
    setXlsxFiles([])
    setProcessedFiles([])
    setDuplicateFiles([])
  }

  const handleProcess = async () => {
    setLoading(true)
    setMessage("Обработка запущена... Ожидайте завершения")
    try {
      const res = await axios.post("http://localhost:8000/process", { sity: city })
      const data = res.data || {}
      if (typeof data === 'object') {
        setMessage(data.status || "Готово")
        setProcessedFiles(Array.isArray(data.processed) ? data.processed : [])
        setDuplicateFiles(Array.isArray(data.duplicates) ? data.duplicates : [])
      } else {
        setMessage("Некорректный ответ от сервера")
      }
    } catch (err) {
      console.error(err)
      setMessage("Ошибка при запуске обработки")
    }
    setLoading(false)
  }

  const handleFetchXlsxFiles = async () => {
    try {
      const res = await axios.get("http://localhost:8000/xlsx-list", {
        params: { sity: city }
      })
      setXlsxFiles(res.data.files || [])
      setMessage(`Найдено файлов: ${res.data.files.length}`)
    } catch (err) {
      setMessage("Ошибка при получении списка файлов")
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      {step === 1 && (
        <div className="max-w-sm w-full space-y-4">
          <h1 className="text-xl font-bold text-center">Вход по городу</h1>
          <input
            type="text"
            placeholder="Город (Moscow, Piter, Novgorod)"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full p-2 border rounded"
          />
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full p-2 border rounded"
          />
          <button
            onClick={handleLogin}
            className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700"
          >
            Войти
          </button>
          {message && <p className="text-red-500 text-sm text-center">{message}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4 text-center">
          <h2 className="text-xl font-semibold">Город: {city}</h2>
          <button
            onClick={handleProcess}
            disabled={loading}
            className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700"
          >
            {loading ? "Обработка..." : "Запустить обработку"}
          </button>
          <button
            onClick={handleFetchXlsxFiles}
            className="bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700"
          >
            Получить список Excel-файлов
          </button>
          <button
            onClick={handleLogout}
            className="bg-gray-500 text-white px-4 py-1 rounded hover:bg-gray-600"
          >
            Выйти
          </button>
          {message && <p className="text-blue-600 mt-2">{message}</p>}

          {processedFiles.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium">Обработанные:</h3>
              <ul className="text-sm text-left">
                {processedFiles.map((file, i) => (
                  <li key={i}>{file}</li>
                ))}
              </ul>
            </div>
          )}

          {duplicateFiles.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium text-yellow-700">Дубликаты:</h3>
              <ul className="text-sm text-left">
                {duplicateFiles.map((file, i) => (
                  <li key={i}>{file}</li>
                ))}
              </ul>
            </div>
          )}

          {xlsxFiles.length > 0 && (
            <div className="mt-4">
              <h3 className="font-medium">Файлы Excel:</h3>
              <ul className="text-sm text-left">
                {xlsxFiles.map((file, i) => (
                  <li key={i}>{file}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
