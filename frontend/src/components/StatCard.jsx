export default function StatCard({ icon: Icon, label, value, color, sub }) {
  const colors = {
    blue: "from-blue-500/20 to-blue-600/5 border-blue-500/30 text-blue-400",
    green:
      "from-green-500/20 to-green-600/5 border-green-500/30 text-green-400",
    red: "from-red-500/20 to-red-600/5 border-red-500/30 text-red-400",
    yellow:
      "from-yellow-500/20 to-yellow-600/5 border-yellow-500/30 text-yellow-400",
    purple:
      "from-purple-500/20 to-purple-600/5 border-purple-500/30 text-purple-400",
    cyan: "from-cyan-500/20 to-cyan-600/5 border-cyan-500/30 text-cyan-400",
    orange:
      "from-orange-500/20 to-orange-600/5 border-orange-500/30 text-orange-400",
  };

  return (
    <div
      className={`bg-gradient-to-br ${colors[color]} border rounded-xl p-5 transition-transform hover:scale-[1.02]`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-[var(--text-secondary)]">{label}</span>
        {Icon && <Icon size={20} className="opacity-60" />}
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      {sub && (
        <p className="text-xs text-[var(--text-secondary)] mt-1">{sub}</p>
      )}
    </div>
  );
}