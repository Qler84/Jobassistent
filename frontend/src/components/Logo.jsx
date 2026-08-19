// Icon bleibt eine Bilddatei (handgezeichnete Wave-Illustration, nicht sinnvoll
// in CSS nachbaubar). Wortmarke + Slogan sind dagegen echter Text - durchsuchbar,
// barrierefrei vorlesbar, verlustfrei skalierbar und ohne zusaetzliches
// Bild-Downloadgewicht, statt in ein Raster-Logo eingebrannt zu sein. Farben
// per Pipette aus der Original-Grafik uebernommen (JOB dunkelblau, ASSISTENT
// hellblau), damit die Optik trotzdem der Vorlage entspricht.
const JOB_COLOR = '#243F64'
const ASSISTENT_COLOR = '#5B9BD5'
const TAGLINE_COLOR = '#3B4A63'

export function LogoMark({ className = 'h-9 w-auto' }) {
  return <img src="/logo-mark.png" alt="" className={`${className} object-contain`} />
}

export function LogoLockup({
  markClassName = 'h-14 w-auto',
  wordmarkClassName = 'text-xl',
  showTagline = true,
  className = '',
}) {
  return (
    <div className={`flex flex-col items-center text-center ${className}`}>
      <LogoMark className={markClassName} />
      <div className={`font-bold uppercase tracking-wide leading-none mt-1.5 ${wordmarkClassName}`}>
        <span style={{ color: JOB_COLOR }}>Job</span>
        <span style={{ color: ASSISTENT_COLOR }}>Assistent</span>
      </div>
      {showTagline && (
        <p className="text-xs mt-1" style={{ color: TAGLINE_COLOR }}>
          smartes Bewerbungsmanagement
        </p>
      )}
    </div>
  )
}
