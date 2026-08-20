import { useEffect, useState } from 'react'
import client, { errorMessage } from '../api/client'

const EMPTY = {
  imap_host: '',
  imap_port: '',
  email_user: '',
  email_password: '',
  claude_model: 'claude-sonnet-5',
  imap_auto_check_enabled: false,
  imap_auto_check_minutes: 30,
  match_threshold: 20,
  auto_send_enabled: false,
}

export default function Einstellungen() {
  const [form, setForm] = useState(EMPTY)
  const [hasPassword, setHasPassword] = useState(false)
  const [senderVerified, setSenderVerified] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveResult, setSaveResult] = useState(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  async function load() {
    try {
      const { data } = await client.get('/settings')
      setForm({
        imap_host: data.imap_host || '',
        imap_port: data.imap_port || '',
        email_user: data.email_user || '',
        email_password: '',
        claude_model: data.claude_model,
        imap_auto_check_enabled: data.imap_auto_check_enabled,
        imap_auto_check_minutes: data.imap_auto_check_minutes,
        match_threshold: data.match_threshold,
        auto_send_enabled: data.auto_send_enabled,
      })
      setHasPassword(data.has_email_password)
      setSenderVerified(data.sender_verified)
    } catch (err) {
      setLoadError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setSaveResult(null)
    try {
      const payload = {
        ...form,
        imap_port: form.imap_port ? Number(form.imap_port) : null,
        // leeres Feld = unveraendert lassen (nicht ueberschreiben), nur bei
        // tatsaechlicher Eingabe wird das gespeicherte Secret ersetzt
        email_password: form.email_password || null,
      }
      await client.put('/settings', payload)
      setSaveResult({ ok: true, text: 'Einstellungen gespeichert.' })
      await load()
    } catch (err) {
      setSaveResult({ ok: false, text: errorMessage(err) })
    } finally {
      setSaving(false)
    }
  }

  async function handleVerifySender() {
    setTesting(true)
    setTestResult(null)
    try {
      const { data } = await client.post('/settings/verify-sender', {
        email_user: form.email_user || null,
      })
      setSenderVerified(data.verifiziert)
      setTestResult({ ok: data.verifiziert, text: data.hinweis })
    } catch (err) {
      setTestResult({ ok: false, text: errorMessage(err) })
    } finally {
      setTesting(false)
    }
  }

  if (loading) return <p className="text-slate-400 text-sm">Lädt…</p>

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-800 mb-6">Einstellungen</h1>

      {loadError && <p className="text-sm text-rose-600 mb-4">{loadError}</p>}

      <form onSubmit={handleSave} className="space-y-6">
        <section className="border border-slate-200 rounded-xl p-5">
          <label className="flex items-center justify-between text-sm font-medium text-slate-600 mb-1.5">
            <span>Match-Schwelle</span>
            <span>{form.match_threshold}%</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={form.match_threshold}
            onChange={(e) => update('match_threshold', Number(e.target.value))}
            className="w-full accent-primary"
          />
          <p className="text-xs text-slate-500 mt-2">
            Stellen unterhalb dieser Match-Schwelle werden bei der Suche gar nicht erst gespeichert oder
            vorgeschlagen (Qualität vor Quantität).
          </p>
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <label className="block text-sm font-medium text-slate-600 mb-1.5">Standard-Modell für Anschreiben</label>
          <select
            value={form.claude_model}
            onChange={(e) => update('claude_model', e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="claude-sonnet-5">claude-sonnet-5</option>
            <option value="claude-opus-5">claude-opus-5</option>
            <option value="claude-haiku-4-5-20251001">claude-haiku-4-5</option>
          </select>

          <label className="flex items-start gap-2 mt-4 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.auto_send_enabled}
              onChange={(e) => update('auto_send_enabled', e.target.checked)}
              className="mt-0.5 accent-primary"
            />
            Automatischen E-Mail-Versand aktivieren
          </label>
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-2">
            Standardmäßig läuft die App im Vorschau-Modus: Anschreiben werden erzeugt und gespeichert, aber NICHT
            automatisch versendet. Erst wenn du das hier aktivierst, kannst du im Bereich „Bewerbungen“ freigegebene
            Anschreiben per Klick tatsächlich versenden – jeder Versand erfordert weiterhin eine explizite
            Bestätigung, es wird nie im Hintergrund automatisch versendet.
          </p>
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <label className="flex items-start gap-2 text-sm text-slate-700 mb-2">
            <input
              type="checkbox"
              checked={form.imap_auto_check_enabled}
              onChange={(e) => update('imap_auto_check_enabled', e.target.checked)}
              className="mt-0.5 accent-primary"
            />
            Postfach automatisch im Hintergrund prüfen
          </label>
          <div className="flex items-center gap-3 mb-2">
            <label className="text-sm font-medium text-slate-600">Prüfintervall</label>
            <select
              value={form.imap_auto_check_minutes}
              onChange={(e) => update('imap_auto_check_minutes', Number(e.target.value))}
              className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
            >
              {[15, 30, 60, 120].map((m) => (
                <option key={m} value={m}>
                  {m} Minuten
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs text-slate-500">
            Auf dem kostenlosen Render-Tier läuft kein dauerhafter Hintergrund-Job – nutze stattdessen „Postfach
            jetzt prüfen“ im Dashboard oder bei den Bewerbungen. Diese Einstellung wird bereits gespeichert, damit
            sie sofort greift, sobald ein geplanter Check (z.B. via Render Cron Job) eingerichtet wird.
          </p>
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-1">Zugangsdaten</h2>
          <p className="text-xs text-slate-400 mb-4">
            Werden verschlüsselt gespeichert. Für web.de/GMX bitte ein App-Passwort statt des Hauptpassworts
            verwenden. IMAP wird für den Postfach-Abruf (Statusverfolgung) genutzt; der Versand selbst läuft
            über einen zentral bereitgestellten E-Mail-Dienst, siehe „Absender-Verifizierung“ unten.
          </p>
          <div className="grid sm:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">IMAP-Host</label>
              <input
                type="text"
                placeholder="imap.web.de"
                value={form.imap_host}
                onChange={(e) => update('imap_host', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">IMAP-Port</label>
              <input
                type="number"
                placeholder="993"
                value={form.imap_port}
                onChange={(e) => update('imap_port', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">E-Mail-Adresse</label>
              <input
                type="email"
                value={form.email_user}
                onChange={(e) => update('email_user', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">
                App-Passwort {hasPassword && <span className="text-slate-400">(hinterlegt)</span>}
              </label>
              <input
                type="password"
                placeholder={hasPassword ? '•••••••••••• (unverändert lassen)' : ''}
                value={form.email_password}
                onChange={(e) => update('email_password', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
          </div>
          <p className="text-xs text-slate-500 mb-4">
            Die Claude-Anschreiben-Generierung wird zentral bereitgestellt – dafür ist kein eigener
            Anthropic-API-Key nötig.
          </p>

          <div className="border-t border-slate-100 pt-4">
            <div className="flex items-center gap-2 mb-1.5">
              <h3 className="text-sm font-medium text-slate-600">Absender-Verifizierung</h3>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  senderVerified ? 'bg-primary-light text-primary-dark' : 'bg-amber-50 text-amber-700'
                }`}
              >
                {senderVerified ? 'verifiziert' : 'nicht verifiziert'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Bewerbungen werden über einen zentralen E-Mail-Dienst versendet (nicht per direktem SMTP, da
              Hosting-Anbieter das oft blockieren). Damit E-Mails wirklich von deiner eigenen Adresse aus
              verschickt werden dürfen, musst du sie einmalig bestätigen: Klick unten löst eine Bestätigungsmail
              an deine E-Mail-Adresse aus, den enthaltenen Link musst du dort anklicken.
            </p>
            <div className="flex items-center gap-3 flex-wrap">
              <button
                type="button"
                onClick={handleVerifySender}
                disabled={testing || senderVerified}
                className="text-xs text-slate-500 border border-slate-200 rounded-lg px-3 py-2 hover:bg-slate-50 disabled:opacity-60"
              >
                {testing ? 'Sende…' : senderVerified ? 'Bereits verifiziert' : 'Verifizierung anstoßen'}
              </button>
              {testResult && (
                <span className={`text-xs ${testResult.ok ? 'text-primary' : 'text-rose-600'}`}>
                  {testResult.text}
                </span>
              )}
            </div>
          </div>
        </section>

        <div>
          <button
            type="submit"
            disabled={saving}
            className="w-full bg-primary text-white text-sm font-medium rounded-lg px-4 py-3 hover:bg-primary-dark transition disabled:opacity-60"
          >
            {saving ? 'Speichert…' : 'Einstellungen speichern'}
          </button>
          {saveResult && (
            <p className={`text-sm mt-2 text-center ${saveResult.ok ? 'text-primary' : 'text-rose-600'}`}>
              {saveResult.text}
            </p>
          )}
        </div>
      </form>
    </div>
  )
}
