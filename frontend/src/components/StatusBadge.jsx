export default function StatusBadge({ status }) {
  const styles = {
    completed: "bg-green-500/20 text-green-400 border-green-500/40",
    running: "bg-blue-500/20 text-blue-400 border-blue-500/40",
    pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
    failed: "bg-red-500/20 text-red-400 border-red-500/40",
    new: "bg-cyan-500/20 text-cyan-400 border-cyan-500/40",
    acknowledged: "bg-blue-500/20 text-blue-400 border-blue-500/40",
    investigating: "bg-purple-500/20 text-purple-400 border-purple-500/40",
    resolved: "bg-green-500/20 text-green-400 border-green-500/40",
    false_positive: "bg-gray-500/20 text-gray-400 border-gray-500/40",
  };

  return (
    <span
      className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
        styles[status] || styles.pending
      }`}
    >
      {status?.replace("_", " ").toUpperCase()}
    </span>
  );
}