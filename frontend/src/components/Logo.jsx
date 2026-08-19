export function LogoMark({ className = 'h-9 w-auto' }) {
  return <img src="/logo-mark.png" alt="JobAssistent" className={`${className} object-contain`} />
}

export function LogoLockup({ markClassName = 'h-9 w-auto', textClassName = 'text-lg', showTagline = false }) {
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
