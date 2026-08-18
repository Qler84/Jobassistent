import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import client, { errorMessage } from '../api/client'
import { AlertIcon, BackIcon, CheckIcon, FileIcon, ResetIcon } from '../components/Icons'
import StatusBadge from '../components/StatusBadge'

export default function AnschreibenVorschau() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [application, setApplication] = useState(null)
  const [attachments, setAttachments] = useState([])
  const [autoSendEnabled, setAutoSendEnabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [saving, setSaving] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [betreff, setBetreff] = useState('')
  const [ansprechpartner, setAnsprechpartner] = useState('')
  const [kontaktEmail, setKontaktEmail] = useState('')
  const [text, setText] = useState('')

  async function load() {
    setLoading(true)
    try {
      const [appRes, attRes, settingsRes] = await Promise.all([
        client.get(`/applications/${id}`),
        client.get('/profile/attachments'),
        client.get('/settings'),
      ])
      setApplication(appRes.data)
      setBetreff(appRes.data.betreff || `Bewerbung als ${appRes.data.job.titel}`)
      setAnsprechpartner(appRes.data.ansprechpartner || '')
      setKontaktEmail(appRes.data.kontakt_email || '')
      setText(appRes.data.anschreiben_text || '')
      setAttachments(attRes.data)
      setAutoSendEnabled(settingsRes.data.auto_send_enabled)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function handleGenerate() {
    setGenerating(true)
    setError('')
    setMessage('')
    try {
      const { data } = await client.post(`/applications/${id}/generate-cover-letter`)
      setText(data.anschreiben_text)
      setBetreff(data.betreff)
      setAnsprechpartner(data.ansprechpartner || '')
      setKontaktEmail(data.kontakt_email || '')
      setMessage('Anschreiben wurde generiert. Bitte prüfen, bevor du freigibst.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setGenerating(false)
    }
  }

  async function saveDraft() {
    setSaving(true)
    setError('')
    try {
      await client.put(`/applications/${id}`, {
        anschreiben_text: text,
        betreff,
        ansprechpartner,
        kontakt_email: kontaktEmail,
      })
      setMessage('Als Entwurf gespeichert.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleSend() {
    setSending(true)
    setError('')
    setMessage('')
    try {
      await client.put(`/applications/${id}`, {
        anschreiben_text: text,
        betreff,
        ansprechpartner,
        kontakt_email: kontaktEmail,
      })
      await client.post(`/applications/${id}/send`)
      navigate('/bewerbungen')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return <p className="text-slate-400 text-sm">Lädt…</p>
  }
  if (!application) {
    return <p className="text-sm text-rose-600">{error || 'Bewerbung nicht gefunden.'}</p>
  }

  const alreadySent = application.status !== 'entwurf'

  return (
    <div className="max-w-4xl">
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-slate-500 hover:text-primary flex items-center gap-1 mb-3"
      >
        <BackIcon className="icon w-4 h-4" />
        Zurück
      </button>
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl font-semibold text-slate-800">Anschreiben-Vorschau</h1>
        <StatusBadge status={application.status} />
      </div>
      <p className="text-slate-500 mb-6">
        {application.job.titel} · {application.job.firma}, {application.job.ort}
      </p>

      {!alreadySent && (
        <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 mb-6 text-sm text-amber-800">
          <AlertIcon className="icon w-4 h-4 mt-0.5 shrink-0" />
          {autoSendEnabled ? (
            <div>
              Automatischer Versand ist aktiviert. Diese Bewerbung wird erst versendet, wenn du unten explizit auf
              „Freigeben &amp; Senden" klickst.
            </div>
          ) : (
            <div>
              <span className="font-medium">Vorschau-Modus aktiv:</span> Der automatische Versand ist in den
              Einstellungen deaktiviert. Aktiviere ihn dort, um Bewerbungen tatsächlich versenden zu können.
            </div>
          )}
        </div>
      )}
      {message && <p className="text-sm text-primary mb-4">{message}</p>}
      {error && <p className="text-sm text-rose-600 mb-4">{error}</p>}

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Ansprechpartner</label>
              <input
                type="text"
                value={ansprechpartner}
                onChange={(e) => setAnsprechpartner(e.target.value)}
                disabled={alreadySent}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:bg-slate-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Empfänger-E-Mail</label>
              <input
                type="email"
                value={kontaktEmail}
                onChange={(e) => setKontaktEmail(e.target.value)}
                disabled={alreadySent}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:bg-slate-50"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Betreff</label>
            <input
              type="text"
              value={betreff}
              onChange={(e) => setBetreff(e.target.value)}
              disabled={alreadySent}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:bg-slate-50"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-medium text-slate-600">Anschreiben</label>
              {!alreadySent && (
                <button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="text-xs text-primary font-medium flex items-center gap-1 disabled:opacity-60"
                >
                  <ResetIcon className="icon w-3.5 h-3.5" />
                  {generating ? 'Generiere…' : text ? 'Neu generieren' : 'Anschreiben generieren'}
                </button>
              )}
            </div>
            <textarea
              rows={16}
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={alreadySent}
              className="w-full rounded-lg border border-slate-200 px-3.5 py-3 text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:bg-slate-50"
            />
          </div>
        </div>

        <div className="space-y-4">
          <div className="border border-slate-200 rounded-xl p-4">
            <div className="text-sm font-medium text-slate-700 mb-3">Anlagen (aus Profil)</div>
            {attachments.length === 0 ? (
              <p className="text-xs text-slate-400">Keine Anlagen hinterlegt.</p>
            ) : (
              <div className="space-y-2">
                {attachments.map((a) => (
                  <div key={a.id} className="flex items-center gap-2 text-sm text-slate-600">
                    <FileIcon className="icon w-4 h-4 text-slate-400" />
                    {a.filename}
                  </div>
                ))}
              </div>
            )}
            <p className="text-xs text-slate-400 mt-3">Werden automatisch mitgesendet, wie im Profil hinterlegt.</p>
          </div>

          <div className="border border-slate-200 rounded-xl p-4">
            <div className="text-sm font-medium text-slate-700 mb-3">Match-Details</div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary-light flex items-center justify-center text-primary-dark font-semibold text-xs">
                {application.job.match_score}%
              </div>
              <span className="text-sm text-slate-600">Übereinstimmung mit deinem Profil</span>
            </div>
          </div>

          {!alreadySent && (
            <div className="border border-slate-200 rounded-xl p-4 space-y-3">
              <button
                onClick={handleSend}
                disabled={sending || !text || !kontaktEmail}
                className="w-full bg-primary text-white text-sm font-medium rounded-lg px-4 py-2.5 hover:bg-primary-dark transition flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <CheckIcon className="icon w-4 h-4" />
                {sending ? 'Wird gesendet…' : 'Freigeben & Senden'}
              </button>
              <button
                onClick={saveDraft}
                disabled={saving}
                className="w-full border border-slate-200 text-slate-600 text-sm font-medium rounded-lg px-4 py-2.5 hover:bg-slate-50 disabled:opacity-60"
              >
                Als Entwurf speichern
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
