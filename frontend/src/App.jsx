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
    <div className="min-h-screen flex flex-col items-center justify-center p-6 font-sans">
      {step === 1 && (
        <div className="bg-white shadow-lg rounded-lg p-8 w-full max-w-md space-y-4">
          <h1 className="text-2xl font-bold text-center text-gray-800">Вход по городу</h1>
          <input
            type="text"
            placeholder="Город (Moscow, Piter, Novgorod)"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button
            onClick={handleLogin}
            className="w-full bg-gray-700 text-white py-3 text-lg rounded-md hover:bg-gray-800"
          >
            Войти
          </button>
          {message && <p className="text-red-500 text-sm text-center">{message}</p>}
        </div>
      )}

      {step === 2 && (
        <div className="space-y-6 text-center w-full max-w-4xl">
          <h2 className="text-2xl font-semibold text-gray-800">Город: {city}</h2>
          <div className="flex flex-wrap gap-4 justify-center">
            <button
              onClick={handleProcess}
              disabled={loading}
              className="bg-gray-600 text-white px-6 py-3 rounded-md text-lg hover:bg-gray-700 disabled:opacity-60"
            >
              {loading ? "Обработка..." : "Запустить обработку"}
            </button>
            <button
              onClick={handleFetchXlsxFiles}
              className="bg-blue-600 text-white px-6 py-3 rounded-md text-lg hover:bg-blue-700"
            >
              Получить список Excel-файлов
            </button>
            <button
              onClick={handleLogout}
              className="bg-red-500 text-white px-6 py-3 rounded-md text-lg hover:bg-red-600"
            >
              Выйти
            </button>
          </div>
          {message && <p className="text-blue-700 mt-2 font-medium">{message}</p>}

          <div className="flex flex-wrap justify-center gap-8 mt-6">
            {processedFiles.length > 0 && (
              <div>
                <h3 className="font-semibold text-lg text-green-700 mb-2">Обработанные</h3>
                <ul className="text-sm text-left bg-white rounded-md shadow p-3 w-64">
                  {processedFiles.map((file, i) => (
                    <li key={i}>{file}</li>
                  ))}
                </ul>
              </div>
            )}

            {duplicateFiles.length > 0 && (
              <div>
                <h3 className="font-semibold text-lg text-yellow-700 mb-2">Дубликаты</h3>
                <ul className="text-sm text-left bg-white rounded-md shadow p-3 w-64">
                  {duplicateFiles.map((file, i) => (
                    <li key={i}>{file}</li>
                  ))}
                </ul>
              </div>
            )}

            {xlsxFiles.length > 0 && (
              <div>
                <h3 className="font-semibold text-lg text-indigo-700 mb-2">Файлы Excel</h3>
                <ul className="text-sm text-left bg-white rounded-md shadow p-3 w-64">
                  {xlsxFiles.map((file, i) => (
                    <li key={i}>{file}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
