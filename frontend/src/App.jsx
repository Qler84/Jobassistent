import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import AnschreibenVorschau from './pages/AnschreibenVorschau'
import Bewerbungen from './pages/Bewerbungen'
import Dashboard from './pages/Dashboard'
import Einstellungen from './pages/Einstellungen'
import Login from './pages/Login'
import Profil from './pages/Profil'
import Register from './pages/Register'
import Stellensuche from './pages/Stellensuche'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/stellensuche" element={<Stellensuche />} />
        <Route path="/bewerbungen" element={<Bewerbungen />} />
        <Route path="/bewerbungen/:id" element={<AnschreibenVorschau />} />
        <Route path="/profil" element={<Profil />} />
        <Route path="/einstellungen" element={<Einstellungen />} />
      </Route>
    </Routes>
  )
}
