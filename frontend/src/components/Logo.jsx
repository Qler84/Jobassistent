export function LogoMark({ className = 'w-9 h-9' }) {
  return <img src="/logo.svg" alt="JobAssistent" className={className} />
}

export function LogoLockup({ markClassName = 'w-9 h-9', textClassName = 'text-lg', showTagline = false }) {
  return (
    <div className="flex items-center gap-2">
      <LogoMark className={markClassName} />
      <div>
        <span className={`font-semibold text-slate-800 ${textClassName}`}>JobAssistent</span>
        {showTagline && <p className="text-xs text-slate-400 -mt-0.5">Das smarte Bewerbungsmanagement.</p>}
      </div>
    </div>
  )
}
