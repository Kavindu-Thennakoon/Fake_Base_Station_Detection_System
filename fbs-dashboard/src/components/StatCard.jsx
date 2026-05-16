export default function StatCard({ title, value, icon: Icon, color = 'blue' }) {
  const colors = {
    blue:   'from-blue-600/20 to-blue-900/10 border-blue-800 text-blue-400',
    red:    'from-red-600/20 to-red-900/10 border-red-800 text-red-400',
    green:  'from-green-600/20 to-green-900/10 border-green-800 text-green-400',
    yellow: 'from-yellow-600/20 to-yellow-900/10 border-yellow-800 text-yellow-400',
  };

  return (
    <div className={`bg-gradient-to-br ${colors[color]} border rounded-xl p-5`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wider text-gray-400">{title}</p>
          <p className="text-3xl font-bold mt-1">{value}</p>
        </div>
        {Icon && <Icon size={32} className="opacity-40" />}
      </div>
    </div>
  );
}