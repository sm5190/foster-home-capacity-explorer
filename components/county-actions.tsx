"use client";

import { useEffect, useRef, useState } from "react";

export function CountyActions() {
  const [copied, setCopied] = useState(false);

  const timeoutReference = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutReference.current) {
        clearTimeout(timeoutReference.current);
      }
    };
  }, []);

  async function copyLink(): Promise<void> {
    try {
      await navigator.clipboard.writeText(window.location.href);

      setCopied(true);

      if (timeoutReference.current) {
        clearTimeout(timeoutReference.current);
      }

      timeoutReference.current = setTimeout(() => {
        setCopied(false);
      }, 2_000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="page-actions">
      <button
        className="button button--secondary"
        onClick={copyLink}
        type="button"
      >
        {copied ? "Link copied" : "Copy shareable link"}
      </button>

      <button
        className="button button--primary"
        onClick={() => window.print()}
        type="button"
      >
        Print county brief
      </button>
    </div>
  );
}
