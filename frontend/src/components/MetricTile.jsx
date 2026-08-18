export default function MetricTile({ label, value, icon: Icon, iconClassName = 'text-primary' }) {
  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-slate-500 text-sm">{label}</span>
        {Icon && <Icon className={`icon w-4 h-4 ${iconClassName}`} />}
      </div>
      <div className="text-3xl font-semibold text-slate-800">{value}</div>
    </div>
  )
}
