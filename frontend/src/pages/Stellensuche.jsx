import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client, { errorMessage } from '../api/client'
import { ExternalLinkIcon, MailIcon } from '../components/Icons'

const ARBEITSZEIT_OPTIONS = [
  { value: '', label: 'Alle' },
  { value: 'vz', label: 'Vollzeit' },
  { value: 'tz', label: 'Teilzeit' },
  { value: 'ho', label: 'Home-Office' },
  { value: 'snw', label: 'Schicht/Nacht/Wochenende' },
  { value: 'mj', label: 'Minijob' },
]

export default function Stellensuche() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    was: '',
    wo: '',
    umkreis: 25,
    veroeffentlicht_seit: 14,
    arbeitszeit: '',
    size: 25,
  })
  const [jobs, setJobs] = useState([])
  const [searching, setSearching] = useState(false)
  const [importing, setImporting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  async function loadJobs() {
    const { data } = await client.get('/jobs', { params: { status_filter: 'neu' } })
    setJobs(data)
  }

  useEffect(() => {
    loadJobs()
  }, [])

  async function handleSearch(e) {
    e.preventDefault()
    setSearching(true)
    setError('')
    setMessage('')
    try {
      const payload = { ...form, arbeitszeit: form.arbeitszeit || null }
      const { data } = await client.post('/jobs/search', payload)
      setMessage(`${data.gefunden} Treffer gefunden, ${data.neu} neu gespeichert.`)
      await loadJobs()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSearching(false)
    }
  }

  async function handleImportAlerts() {
    setImporting(true)
    setError('')
    setMessage('')
    try {
      const { data } = await client.post('/jobs/import-alerts')
      setMessage(`${data.emails_verarbeitet} Job-Alert-Mail(s) ausgewertet, ${data.jobs_neu} neue Treffer.`)
      if (data.fehler.length > 0) {
        setError(data.fehler.join(' · '))
      }
      await loadJobs()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setImporting(false)
    }
  }

  async function handleConfirm(jobId) {
    setBusyId(jobId)
    setError('')
    try {
      const { data } = await client.post(`/jobs/${jobId}/confirm`)
      navigate(`/bewerbungen/${data.id}`)
    } catch (err) {
      setError(errorMessage(err))
      setBusyId(null)
    }
  }

  async function handleReject(jobId) {
    setBusyId(jobId)
    try {
      await client.post(`/jobs/${jobId}/reject`)
      setJobs((prev) => prev.filter((j) => j.id !== jobId))
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="max-w-6xl">
      <h1 className="text-2xl font-semibold text-slate-800 mb-1">Stellensuche</h1>
      <p className="text-slate-500 mb-6">
        Bundesagentur für Arbeit &amp; Job-Alert-E-Mails (LinkedIn, Xing, StepStone, Indeed).
      </p>

      <form onSubmit={handleSearch} className="border border-slate-200 rounded-xl p-5 mb-6">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-2">
            <label className="block text-sm font-medium text-slate-600 mb-1.5">
              Zusätzlicher Suchbegriff (optional)
            </label>
            <input
              type="text"
              placeholder="z.B. Power BI — leer lässt alle Wunschjobtitel aus dem Profil durchsuchen"
              value={form.was}
              onChange={(e) => setForm({ ...form, was: e.target.value })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Ort</label>
            <input
              type="text"
              value={form.wo}
              onChange={(e) => setForm({ ...form, wo: e.target.value })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Umkreis</label>
            <select
              value={form.umkreis}
              onChange={(e) => setForm({ ...form, umkreis: Number(e.target.value) })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              {[10, 25, 50, 100].map((v) => (
                <option key={v} value={v}>
                  {v} km
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Veröffentlicht seit</label>
            <select
              value={form.veroeffentlicht_seit}
              onChange={(e) => setForm({ ...form, veroeffentlicht_seit: Number(e.target.value) })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              {[7, 14, 30].map((v) => (
                <option key={v} value={v}>
                  {v} Tage
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Arbeitszeit</label>
            <select
              value={form.arbeitszeit}
              onChange={(e) => setForm({ ...form, arbeitszeit: e.target.value })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            >
              {ARBEITSZEIT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Max. Treffer</label>
            <input
              type="number"
              min={1}
              max={100}
              value={form.size}
              onChange={(e) => setForm({ ...form, size: Number(e.target.value) })}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 mt-5">
          <button
            type="submit"
            disabled={searching}
            className="bg-primary text-white text-sm font-medium rounded-lg px-5 py-2.5 hover:bg-primary-dark transition disabled:opacity-60"
          >
            {searching ? 'Suche läuft…' : 'Suche starten'}
          </button>
        </div>
      </form>

      <div className="border border-slate-200 rounded-xl p-5 mb-6 bg-slate-50/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="font-medium text-slate-800 text-sm mb-1">Job-Alert-E-Mails importieren</div>
            <p className="text-xs text-slate-500 max-w-xl">
              Kein Scraping: es werden nur E-Mails ausgewertet, die LinkedIn/Xing/StepStone/Indeed dir bereits
              regulär schicken.
            </p>
          </div>
          <button
            onClick={handleImportAlerts}
            disabled={importing}
            className="shrink-0 flex items-center gap-2 border border-primary/30 text-primary text-sm font-medium rounded-lg px-4 py-2 hover:bg-primary-light disabled:opacity-60"
          >
            <MailIcon className="icon w-4 h-4" />
            {importing ? 'Prüfe…' : 'Job-Alert-E-Mails jetzt prüfen'}
          </button>
        </div>
      </div>

      {message && <p className="text-sm text-primary mb-3">{message}</p>}
      {error && <p className="text-sm text-rose-600 mb-3">{error}</p>}

      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-slate-800">
          Ergebnisse <span className="text-slate-400 font-normal">({jobs.length} neue Treffer)</span>
        </h2>
      </div>

      <div className="space-y-3">
        {jobs.length === 0 && (
          <p className="text-sm text-slate-400 border border-slate-200 rounded-xl p-4">
            Noch keine Treffer. Starte oben eine Suche.
          </p>
        )}
        {jobs.map((job) => (
          <div key={job.id} className="border border-slate-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="w-12 h-12 shrink-0 rounded-lg bg-primary-light flex items-center justify-center text-primary-dark font-semibold text-sm">
              {job.match_score}%
            </div>
            <div className="min-w-0 flex-1">
              <div className="font-medium text-slate-800">{job.titel}</div>
              <div className="text-sm text-slate-500">
                {job.firma} · {job.ort}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-medium text-slate-500 border border-slate-200 rounded-lg px-3 py-2 hover:bg-slate-50 flex items-center gap-1"
                >
                  <ExternalLinkIcon className="icon w-3.5 h-3.5" />
                  Anzeige
                </a>
              )}
              <button
                onClick={() => handleConfirm(job.id)}
                disabled={busyId === job.id}
                className="text-xs font-medium text-white bg-primary rounded-lg px-3 py-2 hover:bg-primary-dark disabled:opacity-60"
              >
                Bestätigen
              </button>
              <button
                onClick={() => handleReject(job.id)}
                disabled={busyId === job.id}
                className="text-xs font-medium text-slate-400 border border-slate-200 rounded-lg px-3 py-2 hover:bg-slate-50 disabled:opacity-60"
              >
                Ablehnen
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
