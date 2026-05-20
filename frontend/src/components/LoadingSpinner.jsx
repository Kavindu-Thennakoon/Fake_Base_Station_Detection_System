export default function LoadingSpinner({ text = "Loading..." }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-10 h-10 border-4 border-[var(--border-color)] border-t-[var(--accent-blue)] rounded-full animate-spin mb-4" />
      <p className="text-[var(--text-secondary)] text-sm">{text}</p>
    </div>
  );
}