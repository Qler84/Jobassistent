import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { LogoMark } from '../components/Logo'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(email, password, displayName)
      navigate('/')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-1">
          <LogoMark className="w-10 h-10" />
          <span className="font-semibold text-xl text-slate-800">JobAssistent</span>
        </div>
        <p className="text-xs text-slate-400 text-center mb-7">Das smarte Bewerbungsmanagement.</p>
        <h1 className="text-xl font-semibold text-slate-800 mb-1 text-center">Konto erstellen</h1>
        <p className="text-slate-500 text-sm text-center mb-6">Jeder Nutzer hat sein eigenes, getrenntes Profil.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Name</label>
            <input
              type="text"
              required
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">E-Mail</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 mb-1.5">Passwort</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
            />
            <p className="text-xs text-slate-400 mt-1">Mindestens 8 Zeichen.</p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-white text-sm font-medium rounded-lg px-4 py-2.5 hover:bg-primary-dark transition disabled:opacity-60"
          >
            {loading ? 'Wird erstellt…' : 'Konto erstellen'}
          </button>
        </form>

        <p className="text-sm text-slate-500 text-center mt-6">
          Bereits ein Konto?{' '}
          <Link to="/login" className="text-primary font-medium">
            Anmelden
          </Link>
        </p>
      </div>
    </div>
  )
}
