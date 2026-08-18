import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import client, { errorMessage } from '../api/client'
import { CheckIcon, RefreshIcon, SearchIcon, SendIcon, XIcon } from '../components/Icons'
import MetricTile from '../components/MetricTile'
import { useAuth } from '../context/AuthContext'

const ACTIVITY_ICON = {
  einladung: { icon: CheckIcon, bg: 'bg-emerald-50', color: 'text-emerald-600' },
  absage: { icon: XIcon, bg: 'bg-rose-50', color: 'text-rose-500' },
  versendet: { icon: SendIcon, bg: 'bg-primary-light', color: 'text-primary-dark' },
}

function activityLabel(status) {
  const labels = {
    entwurf: 'Entwurf erstellt',
    freigegeben: 'Anschreiben freigegeben',
    versendet: 'Bewerbung versendet',
    antwort_erhalten: 'Antwort erhalten',
    einladung: 'Einladung erhalten',
    absage: 'Absage erhalten',
    keine_rueckmeldung: 'Keine Rückmeldung',
  }
  return labels[status] || status
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export default function Dashboard() {
  const { user } = useAuth()
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)
  const [checkResult, setCheckResult] = useState('')

  async function loadSummary() {
    try {
      const { data } = await client.get('/dashboard/summary')
      setSummary(data)
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  useEffect(() => {
    loadSummary()
  }, [])

  async function checkInbox() {
    setChecking(true)
    setCheckResult('')
    try {
      const { data } = await client.post('/applications/check-inbox')
      setCheckResult(`${data.aktualisiert} Bewerbung(en) aktualisiert.`)
      await loadSummary()
    } catch (err) {
      setCheckResult(errorMessage(err))
    } finally {
      setChecking(false)
    }
  }

  const firstName = (user?.display_name || '').split(' ')[0]

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-1 gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Guten Tag{firstName ? `, ${firstName}` : ''}</h1>
        <button
          onClick={checkInbox}
          disabled={checking}
          className="hidden sm:flex items-center gap-2 text-sm text-primary font-medium border border-primary/30 rounded-lg px-3 py-2 hover:bg-primary-light disabled:opacity-60"
        >
          <RefreshIcon className="icon w-4 h-4" />
          {checking ? 'Prüfe…' : 'Postfach jetzt prüfen'}
        </button>
      </div>
      <p className="text-slate-500 mb-2">Hier ist dein Überblick über die aktuelle Jobsuche.</p>
      {checkResult && <p className="text-sm text-primary mb-4">{checkResult}</p>}
      {error && <p className="text-sm text-rose-600 mb-4">{error}</p>}

      {!summary ? (
        <p className="text-slate-400 text-sm">Lädt…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-8">
            <MetricTile label="Neue Treffer" value={summary.neue_treffer} icon={SearchIcon} />
            <MetricTile label="Versendet" value={summary.versendet} icon={SendIcon} />
            <MetricTile
              label="Einladungen"
              value={summary.einladungen}
              icon={CheckIcon}
              iconClassName="text-emerald-500"
            />
            <MetricTile label="Absagen" value={summary.absagen} icon={XIcon} iconClassName="text-rose-400" />
          </div>

          <div className="grid lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-slate-800">Neue Matches</h2>
                <Link to="/stellensuche" className="text-sm text-primary font-medium">
                  Alle ansehen →
                </Link>
              </div>
              {summary.neue_matches.length === 0 ? (
                <p className="text-sm text-slate-400 border border-slate-200 rounded-xl p-4">
                  Noch keine neuen Treffer. Starte eine Suche im Bereich Stellensuche.
                </p>
              ) : (
                <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
                  {summary.neue_matches.map((job) => (
                    <div key={job.id} className="flex items-center gap-4 p-4">
                      <div className="w-11 h-11 shrink-0 rounded-lg bg-primary-light flex items-center justify-center text-primary-dark font-semibold text-sm">
                        {job.match_score}%
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-slate-800 truncate">{job.titel}</div>
                        <div className="text-sm text-slate-500 truncate">
                          {job.firma} · {job.ort}
                        </div>
                      </div>
                      <Link
                        to="/stellensuche"
                        className="text-xs font-medium border border-slate-200 rounded-lg px-3 py-1.5 text-slate-600 hover:bg-slate-50 shrink-0"
                      >
                        Ansehen
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="lg:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-slate-800">Letzte Aktivität</h2>
                <Link to="/bewerbungen" className="text-sm text-primary font-medium">
                  Tracker →
                </Link>
              </div>
              {summary.letzte_aktivitaet.length === 0 ? (
                <p className="text-sm text-slate-400 border border-slate-200 rounded-xl p-4">
                  Noch keine Bewerbungen.
                </p>
              ) : (
                <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
                  {summary.letzte_aktivitaet.map((app) => {
                    const meta = ACTIVITY_ICON[app.status] || {
                      icon: SendIcon,
                      bg: 'bg-slate-50',
                      color: 'text-slate-400',
                    }
                    const Icon = meta.icon
                    return (
                      <div key={app.id} className="flex items-start gap-3 p-4">
                        <div className={`w-8 h-8 shrink-0 rounded-full ${meta.bg} flex items-center justify-center`}>
                          <Icon className={`icon w-4 h-4 ${meta.color}`} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm text-slate-800">
                            <span className="font-medium">{activityLabel(app.status)}</span> · {app.job.firma}
                          </div>
                          <div className="text-xs text-slate-400">
                            {formatDate(app.versendet_am || app.erstellt_am)}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
