const STATUS_STYLES = {
  entwurf: { label: 'Entwurf', className: 'bg-slate-50 text-slate-500' },
  freigegeben: { label: 'Freigegeben', className: 'bg-primary-light text-primary-dark' },
  versendet: { label: 'Versendet', className: 'bg-primary-light text-primary-dark' },
  antwort_erhalten: { label: 'Antwort erhalten', className: 'bg-amber-50 text-amber-700' },
  einladung: { label: 'Einladung', className: 'bg-emerald-50 text-emerald-700' },
  absage: { label: 'Absage', className: 'bg-rose-50 text-rose-600' },
  keine_rueckmeldung: { label: 'Keine Rückmeldung', className: 'bg-slate-100 text-slate-600' },
}

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || { label: status, className: 'bg-slate-100 text-slate-600' }
  return (
    <span
      className={`inline-block text-[11px] font-semibold px-2.5 py-1 rounded-full whitespace-nowrap ${style.className}`}
    >
      {style.label}
    </span>
  )
}

export { STATUS_STYLES }
