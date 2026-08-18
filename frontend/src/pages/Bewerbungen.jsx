import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client, { errorMessage } from '../api/client'
import { RefreshIcon } from '../components/Icons'
import StatusBadge from '../components/StatusBadge'

const FILTERS = [
  { value: '', label: 'Alle' },
  { value: 'versendet', label: 'Versendet' },
  { value: 'einladung', label: 'Einladung' },
  { value: 'absage', label: 'Absage' },
  { value: 'keine_rueckmeldung', label: 'Keine Rückmeldung' },
]

function formatDate(iso) {
  if (!iso) return '–'
  return new Date(iso).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export default function Bewerbungen() {
  const navigate = useNavigate()
  const [applications, setApplications] = useState([])
  const [filter, setFilter] = useState('')
  const [checking, setChecking] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function load() {
    try {
      const { data } = await client.get('/applications', {
        params: filter ? { status_filter: filter } : {},
      })
      setApplications(data)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter])

  async function checkInbox() {
    setChecking(true)
    setMessage('')
    try {
      const { data } = await client.post('/applications/check-inbox')
      setMessage(`${data.aktualisiert} Bewerbung(en) aktualisiert.`)
      await load()
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-1">
        <h1 className="text-2xl font-semibold text-slate-800">Bewerbungen</h1>
        <button
          onClick={checkInbox}
          disabled={checking}
          className="flex items-center gap-2 text-sm text-primary font-medium border border-primary/30 rounded-lg px-3 py-2 hover:bg-primary-light self-start sm:self-auto disabled:opacity-60"
        >
          <RefreshIcon className="icon w-4 h-4" />
          {checking ? 'Prüfe…' : 'Postfach jetzt prüfen'}
        </button>
      </div>
      <p className="text-slate-500 mb-6">Alle versendeten Bewerbungen und ihr aktueller Status.</p>
      {message && <p className="text-sm text-primary mb-4">{message}</p>}
      {error && <p className="text-sm text-rose-600 mb-4">{error}</p>}

      <div className="flex flex-wrap gap-2 mb-5">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`text-xs font-medium px-3 py-1.5 rounded-full ${
              filter === f.value ? 'bg-primary text-white' : 'border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {applications.length === 0 ? (
        <p className="text-sm text-slate-400 border border-slate-200 rounded-xl p-4">Keine Bewerbungen gefunden.</p>
      ) : (
        <>
          <div className="hidden md:block border border-slate-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 text-slate-500 text-left">
                  <th className="px-4 py-3 font-medium">Titel</th>
                  <th className="px-4 py-3 font-medium">Firma</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Quelle</th>
                  <th className="px-4 py-3 font-medium">Versendet am</th>
                  <th className="px-4 py-3 font-medium">Aktionen</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {applications.map((app) => (
                  <tr key={app.id}>
                    <td className="px-4 py-3 font-medium text-slate-800">{app.job.titel}</td>
                    <td className="px-4 py-3 text-slate-600">{app.job.firma}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={app.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-500 capitalize">{app.status_quelle}</td>
                    <td className="px-4 py-3 text-slate-500">{formatDate(app.versendet_am)}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => navigate(`/bewerbungen/${app.id}`)} className="text-primary font-medium">
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="md:hidden space-y-3">
            {applications.map((app) => (
              <div key={app.id} className="border border-slate-200 rounded-xl p-4">
                <div className="flex items-start justify-between gap-3 mb-1">
                  <div className="font-medium text-slate-800">{app.job.titel}</div>
                  <StatusBadge status={app.status} />
                </div>
                <div className="text-sm text-slate-500 mb-2">{app.job.firma}</div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="capitalize">
                    {app.status_quelle} · {formatDate(app.versendet_am)}
                  </span>
                  <button onClick={() => navigate(`/bewerbungen/${app.id}`)} className="text-primary font-medium">
                    Details
                  </button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
