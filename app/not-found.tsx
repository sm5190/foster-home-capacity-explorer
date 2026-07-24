import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="page-shell page-shell--narrow">
      <section className="empty-state">
        <p className="eyebrow">Not found</p>

        <h1>The requested county could not be found</h1>

        <p>Check the county name or return to the statewide priority table.</p>

        <Link className="button button--primary" href="/">
          Return to priorities
        </Link>
      </section>
    </div>
  );
}
