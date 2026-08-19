import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { DashboardIcon, MailIcon, SearchIcon, SettingsIcon, UserIcon } from './Icons'
import { LogoMark } from './Logo'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: DashboardIcon, end: true },
  { to: '/stellensuche', label: 'Stellensuche', icon: SearchIcon },
  { to: '/bewerbungen', label: 'Bewerbungen', icon: MailIcon },
  { to: '/profil', label: 'Profil', icon: UserIcon },
  { to: '/einstellungen', label: 'Einstellungen', icon: SettingsIcon },
]

function navClasses(isActive, variant) {
  if (variant === 'desktop') {
    return [
      'flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium',
      isActive ? 'bg-primary-light text-primary-dark' : 'text-slate-600 hover:bg-slate-50 font-normal',
    ].join(' ')
  }
  return ['flex flex-col items-center gap-0.5', isActive ? 'text-primary font-medium' : 'text-slate-400'].join(' ')
}

export default function Layout() {
  const { user, logout } = useAuth()
  const initials = (user?.display_name || '?')
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <div className="bg-white text-slate-800 min-h-screen">
      <header className="lg:hidden flex items-center justify-between px-4 h-14 border-b border-slate-200 sticky top-0 bg-white z-20">
        <div className="flex items-center gap-2">
          <LogoMark className="w-8 h-8" />
          <span className="font-semibold text-slate-800">JobAssistent</span>
        </div>
      </header>

      <div className="flex">
        <aside className="hidden lg:flex flex-col w-64 h-screen sticky top-0 border-r border-slate-200 px-4 py-6">
          <div className="flex items-center gap-2 px-2 mb-1">
            <LogoMark className="w-9 h-9" />
            <span className="font-semibold text-lg text-slate-800">JobAssistent</span>
          </div>
          <p className="text-xs text-slate-400 px-2 mb-7">Das smarte Bewerbungsmanagement.</p>
          <nav className="flex flex-col gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={({ isActive }) => navClasses(isActive, 'desktop')}>
                <Icon />
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto px-2 py-3 rounded-lg bg-slate-50 flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary-dark text-sm font-semibold">
              {initials}
            </div>
            <div className="text-sm min-w-0 flex-1">
              <div className="font-medium text-slate-800 truncate">{user?.display_name}</div>
              <button onClick={logout} className="text-slate-500 text-xs hover:text-primary">
                Abmelden
              </button>
            </div>
          </div>
        </aside>

        <main className="flex-1 px-4 py-6 lg:px-10 lg:py-8 pb-24 lg:pb-8 min-w-0">
          <Outlet />
        </main>
      </div>

      <nav className="lg:hidden fixed bottom-0 inset-x-0 bg-white border-t border-slate-200 flex items-center justify-around h-16 z-20">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => navClasses(isActive, 'mobile')}>
            <Icon />
            <span className="text-[11px]">{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
