import { useEffect, useRef, useState } from 'react'
import client, { errorMessage } from '../api/client'
import { FileIcon, ResetIcon, UploadIcon, XIcon } from '../components/Icons'

const EMPTY_PROFILE = {
  name: '',
  adresse: '',
  telefon: '',
  email: '',
  wunschjobtitel: [],
  wunschort: '',
  umkreis_km: 25,
  arbeitszeit: 'vz',
  berufserfahrung: [],
  ausbildung: [],
  skills: [],
  sprachen: [],
  zertifikate: [],
  cover_letter_hinweise: '',
}

function TagInput({ label, values, onChange, placeholder }) {
  const [input, setInput] = useState('')

  function add() {
    const v = input.trim()
    if (v && !values.includes(v)) onChange([...values, v])
    setInput('')
  }

  return (
    <div>
      <label className="block text-sm font-medium text-slate-600 mb-1.5">{label}</label>
      {values.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {values.map((v) => (
            <span
              key={v}
              className="flex items-center gap-1.5 bg-primary-light text-primary-dark text-sm rounded-full pl-3 pr-2 py-1"
            >
              {v}
              <button
                type="button"
                onClick={() => onChange(values.filter((x) => x !== v))}
                className="text-primary-dark/50 hover:text-primary-dark"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <input
        type="text"
        value={input}
        placeholder={placeholder}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            add()
          }
        }}
        onBlur={add}
        className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
      />
    </div>
  )
}

export default function Profil() {
  const [profile, setProfile] = useState(EMPTY_PROFILE)
  const [attachments, setAttachments] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [importing, setImporting] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const importInputRef = useRef(null)
  const attachmentInputRef = useRef(null)

  async function load() {
    try {
      const [profileRes, attRes] = await Promise.all([
        client.get('/profile'),
        client.get('/profile/attachments'),
      ])
      setProfile(profileRes.data)
      setAttachments(attRes.data)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  function update(field, value) {
    setProfile((p) => ({ ...p, [field]: value }))
  }

  function updateListItem(field, index, key, value) {
    setProfile((p) => {
      const list = [...p[field]]
      list[index] = { ...list[index], [key]: value }
      return { ...p, [field]: list }
    })
  }

  function addListItem(field, empty) {
    setProfile((p) => ({ ...p, [field]: [...p[field], empty] }))
  }

  function removeListItem(field, index) {
    setProfile((p) => ({ ...p, [field]: p[field].filter((_, i) => i !== index) }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const { data } = await client.put('/profile', profile)
      setProfile(data)
      setMessage('Profil gespeichert.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleReset() {
    if (!window.confirm('Profildaten wirklich zurücksetzen? Das kann nicht rückgängig gemacht werden.')) return
    try {
      const { data } = await client.post('/profile/reset')
      setProfile(data)
      setMessage('Profildaten wurden zurückgesetzt.')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  async function handleImportPdf(e) {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return
    setImporting(true)
    setError('')
    setMessage('')
    try {
      const formData = new FormData()
      files.forEach((f) => formData.append('files', f))
      const { data } = await client.post('/profile/import-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setProfile((p) => ({
        ...p,
        name: data.name || p.name,
        adresse: data.adresse || p.adresse,
        telefon: data.telefon || p.telefon,
        email: data.email || p.email,
        wunschjobtitel: data.wunschjobtitel?.length ? data.wunschjobtitel : p.wunschjobtitel,
        berufserfahrung: data.berufserfahrung?.length ? data.berufserfahrung : p.berufserfahrung,
        ausbildung: data.ausbildung?.length ? data.ausbildung : p.ausbildung,
        skills: data.skills?.length ? data.skills : p.skills,
        sprachen: data.sprachen?.length ? data.sprachen : p.sprachen,
        zertifikate: data.zertifikate?.length ? data.zertifikate : p.zertifikate,
      }))
      setMessage('Formular wurde vorausgefüllt - bitte prüfen und dann speichern.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setImporting(false)
      if (importInputRef.current) importInputRef.current.value = ''
    }
  }

  async function handleUploadAttachment(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await client.post('/profile/attachments', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setAttachments((prev) => [...prev, data])
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      if (attachmentInputRef.current) attachmentInputRef.current.value = ''
    }
  }

  async function handleDeleteAttachment(id) {
    try {
      await client.delete(`/profile/attachments/${id}`)
      setAttachments((prev) => prev.filter((a) => a.id !== id))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  if (loading) return <p className="text-slate-400 text-sm">Lädt…</p>

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold text-slate-800 mb-1">Profil</h1>
      <p className="text-slate-500 mb-6">Deine Bewerberdaten für Matching und Anschreiben-Generierung.</p>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <button
          type="button"
          onClick={() => importInputRef.current?.click()}
          disabled={importing}
          className="flex-1 flex items-center justify-center gap-2 border border-primary/30 text-primary text-sm font-medium rounded-lg px-4 py-2.5 hover:bg-primary-light disabled:opacity-60"
        >
          <UploadIcon className="icon w-4 h-4" />
          {importing ? 'Analysiere…' : 'Aus Lebenslauf/Zeugnissen importieren'}
        </button>
        <input
          ref={importInputRef}
          type="file"
          accept="application/pdf"
          multiple
          hidden
          onChange={handleImportPdf}
        />
        <button
          type="button"
          onClick={handleReset}
          className="flex-1 flex items-center justify-center gap-2 border border-slate-200 text-slate-500 text-sm font-medium rounded-lg px-4 py-2.5 hover:bg-slate-50"
        >
          <ResetIcon className="icon w-4 h-4" />
          Profildaten zurücksetzen
        </button>
      </div>

      {message && <p className="text-sm text-primary mb-4">{message}</p>}
      {error && <p className="text-sm text-rose-600 mb-4">{error}</p>}

      <form onSubmit={handleSave} className="space-y-6">
        <section className="border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">Persönliche Angaben</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Name</label>
              <input
                type="text"
                value={profile.name}
                onChange={(e) => update('name', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Adresse</label>
              <input
                type="text"
                placeholder="Straße Hausnummer, PLZ Ort"
                value={profile.adresse}
                onChange={(e) => update('adresse', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Telefon</label>
              <input
                type="text"
                value={profile.telefon}
                onChange={(e) => update('telefon', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">E-Mail</label>
              <input
                type="email"
                value={profile.email}
                onChange={(e) => update('email', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              />
            </div>
          </div>
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">Wunschposition</h2>
          <div className="mb-4">
            <TagInput
              label="Gesuchte Jobtitel (für Suche & Matching)"
              values={profile.wunschjobtitel}
              onChange={(v) => update('wunschjobtitel', v)}
              placeholder="Jobtitel eingeben und Enter drücken…"
            />
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Wunschort</label>
              <input
                type="text"
                value={profile.wunschort}
                onChange={(e) => update('wunschort', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Umkreis</label>
              <select
                value={profile.umkreis_km}
                onChange={(e) => update('umkreis_km', Number(e.target.value))}
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
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Arbeitszeit</label>
              <select
                value={profile.arbeitszeit}
                onChange={(e) => update('arbeitszeit', e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="vz">Vollzeit</option>
                <option value="tz">Teilzeit</option>
                <option value="ho">Home-Office</option>
                <option value="snw">Schicht/Nacht/Wochenende</option>
                <option value="mj">Minijob</option>
              </select>
            </div>
          </div>
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Berufserfahrung</h2>
            <button
              type="button"
              onClick={() => addListItem('berufserfahrung', { firma: '', position: '', zeitraum: '', beschreibung: '' })}
              className="text-xs text-primary font-medium"
            >
              + Hinzufügen
            </button>
          </div>
          <div className="space-y-3">
            {profile.berufserfahrung.map((e, i) => (
              <div key={i} className="border border-slate-100 rounded-lg p-3 space-y-2">
                <div className="flex justify-end">
                  <button type="button" onClick={() => removeListItem('berufserfahrung', i)} className="text-slate-300 hover:text-rose-500">
                    <XIcon className="icon w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="grid sm:grid-cols-2 gap-2">
                  <input
                    placeholder="Position"
                    value={e.position}
                    onChange={(ev) => updateListItem('berufserfahrung', i, 'position', ev.target.value)}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                  />
                  <input
                    placeholder="Firma"
                    value={e.firma}
                    onChange={(ev) => updateListItem('berufserfahrung', i, 'firma', ev.target.value)}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                  />
                </div>
                <input
                  placeholder="Zeitraum (z.B. 2022 - heute)"
                  value={e.zeitraum}
                  onChange={(ev) => updateListItem('berufserfahrung', i, 'zeitraum', ev.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                />
                <textarea
                  placeholder="Beschreibung"
                  rows={2}
                  value={e.beschreibung}
                  onChange={(ev) => updateListItem('berufserfahrung', i, 'beschreibung', ev.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                />
              </div>
            ))}
            {profile.berufserfahrung.length === 0 && <p className="text-xs text-slate-400">Noch keine Einträge.</p>}
          </div>
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Ausbildung</h2>
            <button
              type="button"
              onClick={() => addListItem('ausbildung', { institution: '', abschluss: '', zeitraum: '' })}
              className="text-xs text-primary font-medium"
            >
              + Hinzufügen
            </button>
          </div>
          <div className="space-y-3">
            {profile.ausbildung.map((a, i) => (
              <div key={i} className="border border-slate-100 rounded-lg p-3 space-y-2">
                <div className="flex justify-end">
                  <button type="button" onClick={() => removeListItem('ausbildung', i)} className="text-slate-300 hover:text-rose-500">
                    <XIcon className="icon w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="grid sm:grid-cols-2 gap-2">
                  <input
                    placeholder="Abschluss"
                    value={a.abschluss}
                    onChange={(ev) => updateListItem('ausbildung', i, 'abschluss', ev.target.value)}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                  />
                  <input
                    placeholder="Institution"
                    value={a.institution}
                    onChange={(ev) => updateListItem('ausbildung', i, 'institution', ev.target.value)}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                  />
                </div>
                <input
                  placeholder="Zeitraum"
                  value={a.zeitraum}
                  onChange={(ev) => updateListItem('ausbildung', i, 'zeitraum', ev.target.value)}
                  className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                />
              </div>
            ))}
            {profile.ausbildung.length === 0 && <p className="text-xs text-slate-400">Noch keine Einträge.</p>}
          </div>
        </section>

        <section className="border border-slate-200 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Kenntnisse</h2>
          <TagInput
            label="Skills"
            values={profile.skills}
            onChange={(v) => update('skills', v)}
            placeholder="Skill eingeben und Enter drücken…"
          />
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">Sprachen</label>
              <div className="space-y-2">
                {profile.sprachen.map((s, i) => (
                  <div key={i} className="flex gap-2">
                    <input
                      placeholder="Sprache"
                      value={s.sprache}
                      onChange={(ev) => updateListItem('sprachen', i, 'sprache', ev.target.value)}
                      className="flex-1 rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                    />
                    <input
                      placeholder="Niveau"
                      value={s.niveau}
                      onChange={(ev) => updateListItem('sprachen', i, 'niveau', ev.target.value)}
                      className="w-24 rounded-lg border border-slate-200 px-3 py-1.5 text-sm"
                    />
                    <button type="button" onClick={() => removeListItem('sprachen', i)} className="text-slate-300 hover:text-rose-500">
                      <XIcon className="icon w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => addListItem('sprachen', { sprache: '', niveau: '' })}
                  className="text-xs text-primary font-medium"
                >
                  + Hinzufügen
                </button>
              </div>
            </div>
            <TagInput
              label="Zertifikate"
              values={profile.zertifikate}
              onChange={(v) => update('zertifikate', v)}
              placeholder="Zertifikat eingeben und Enter drücken…"
            />
          </div>
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">Anlagen</h2>
          <p className="text-xs text-slate-400 mb-3">Werden automatisch an jede versendete Bewerbung angehängt.</p>
          <div className="space-y-2 mb-3">
            {attachments.map((a) => (
              <div key={a.id} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <FileIcon className="icon w-4 h-4 text-slate-400" />
                  {a.filename}
                </div>
                <button onClick={() => handleDeleteAttachment(a.id)} className="text-slate-300 hover:text-rose-500">
                  ×
                </button>
              </div>
            ))}
            {attachments.length === 0 && <p className="text-xs text-slate-400">Noch keine Anlagen hochgeladen.</p>}
          </div>
          <button
            type="button"
            onClick={() => attachmentInputRef.current?.click()}
            className="text-xs text-primary font-medium border border-primary/30 rounded-lg px-3 py-2 hover:bg-primary-light"
          >
            + Datei hochladen
          </button>
          <input ref={attachmentInputRef} type="file" hidden onChange={handleUploadAttachment} />
        </section>

        <section className="border border-slate-200 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">Anschreiben-Anpassung</h2>
          <label className="block text-sm font-medium text-slate-600 mb-1.5">
            Zusätzliche Hinweise für die Anschreiben-Generierung
          </label>
          <textarea
            rows={3}
            placeholder="z.B. Ton eher zurückhaltend, Gehaltsvorstellung nicht erwähnen…"
            value={profile.cover_letter_hinweise}
            onChange={(e) => update('cover_letter_hinweise', e.target.value)}
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
          />
        </section>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-primary text-white text-sm font-medium rounded-lg px-4 py-3 hover:bg-primary-dark transition disabled:opacity-60"
        >
          {saving ? 'Speichert…' : 'Profil speichern'}
        </button>
      </form>
    </div>
  )
}
