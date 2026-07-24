export default function LoadingPage() {
  return (
    <div
      aria-busy="true"
      aria-label="Loading county priorities"
      className="page-shell loading-shell"
    >
      <div className="skeleton skeleton--eyebrow" />
      <div className="skeleton skeleton--title" />
      <div className="skeleton skeleton--text" />

      <div className="loading-card-grid">
        {Array.from({
          length: 4,
        }).map((_, index) => (
          <div className="skeleton skeleton--card" key={index} />
        ))}
      </div>

      <div className="skeleton skeleton--table" />
    </div>
  );
}
