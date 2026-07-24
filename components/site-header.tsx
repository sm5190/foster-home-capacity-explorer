import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link className="site-brand" href="/">
          <span className="site-brand__mark">FI</span>

          <span>
            {/* <span className="site-brand__name">Foster Insights</span> */}

            <span className="site-brand__product">
              Illinois Foster Home Capacity Explorer
            </span>
          </span>
        </Link>

        <nav aria-label="Primary navigation" className="primary-navigation">
          <Link href="/">Priorities</Link>

          <Link href="/methodology">About the Data</Link>
        </nav>
      </div>
    </header>
  );
}
