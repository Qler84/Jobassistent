import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import client from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const { data } = await client.get('/auth/me')
      setUser(data)
    } catch {
      localStorage.removeItem('token')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  async function login(email, password) {
    const { data } = await client.post('/auth/login', { email, password })
    localStorage.setItem('token', data.access_token)
    await loadUser()
  }

  async function register(email, password, displayName) {
    const { data } = await client.post('/auth/register', {
      email,
      password,
      display_name: displayName,
    })
    localStorage.setItem('token', data.access_token)
    await loadUser()
  }

  function logout() {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
