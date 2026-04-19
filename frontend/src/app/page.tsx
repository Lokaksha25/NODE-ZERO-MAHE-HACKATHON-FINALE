"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";

const Globe = dynamic(() => import("@/components/globe").then((m) => m.Globe), {
  ssr: false,
  loading: () => <div className="aspect-square w-full animate-pulse rounded-full bg-[var(--border)]" />,
});

export default function LandingPage() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("theme") as "light" | "dark" | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.setAttribute("data-theme", saved);
    }
  }, []);

  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
  }

  const isDark = theme === "dark";

  return (
    <div className="landing-root" data-theme={theme}>
      {/* ─── Nav ─── */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-logo">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
              <circle cx="14" cy="14" r="13" stroke={isDark ? "#fff" : "#111"} strokeWidth="2" />
              <circle cx="14" cy="14" r="4" fill={isDark ? "#fff" : "#111"} />
              <path d="M14 1v26M1 14h26" stroke={isDark ? "#fff" : "#111"} strokeWidth="1" opacity="0.3" />
              <ellipse cx="14" cy="14" rx="8" ry="13" stroke={isDark ? "#fff" : "#111"} strokeWidth="1" opacity="0.3" />
            </svg>
            <span className="landing-logo-text">Reachbl</span>
          </div>

          <div className="landing-nav-links">
            <a href="#features" className="landing-link">Features</a>
            <a href="#how-it-works" className="landing-link">How it works</a>

            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className={`theme-toggle ${isDark ? "is-dark" : ""}`}
              aria-label="Toggle theme"
            >
              <div className="theme-toggle-knob" />
            </button>
          </div>
        </div>
      </nav>

      {/* ─── Hero ─── */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <div className="landing-hero-left animate-rise">
            <div className="landing-badge">
              <span className="landing-badge-dot" />
              Connectivity-Aware Routing
            </div>

            <h1 className="landing-title">
              Reachbl
            </h1>

            <p className="landing-subtitle">
              Routes that understand your signal. We predict connectivity dead zones before
              you reach them — and intelligently defer notifications so you stay focused on
              the road.
            </p>

            <div className="landing-cta-row">
              <Link href="/dashboard" className="landing-btn-primary">
                Get Started
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ marginLeft: 8 }}>
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
              <a href="#how-it-works" className="landing-btn-secondary">
                Learn More
              </a>
            </div>

            <div className="landing-stats">
              <div className="landing-stat">
                <span className="landing-stat-value">100m</span>
                <span className="landing-stat-label">Segment Resolution</span>
              </div>
              <div className="landing-stat-divider" />
              <div className="landing-stat">
                <span className="landing-stat-value">2</span>
                <span className="landing-stat-label">Operators Supported</span>
              </div>
              <div className="landing-stat-divider" />
              <div className="landing-stat">
                <span className="landing-stat-value">3</span>
                <span className="landing-stat-label">Zone Classifications</span>
              </div>
            </div>
          </div>

          <div className="landing-hero-right">
            {mounted && <Globe className="landing-globe" dark={isDark} />}
          </div>
        </div>
      </section>

      {/* ─── Features ─── */}
      <section id="features" className="landing-section">
        <h2 className="landing-section-title">Built for the road ahead</h2>
        <div className="landing-features-grid">
          {[
            {
              icon: "📡",
              title: "Operator-Specific Scoring",
              desc: "Per-carrier connectivity analysis using real cell tower infrastructure data from OpenCellID.",
            },
            {
              icon: "🛡️",
              title: "Safety Mode",
              desc: "Amplifies weak-zone penalties and enforces conservative notification timing to keep drivers focused.",
            },
            {
              icon: "🔔",
              title: "Geo-Deferred Notifications",
              desc: "Non-urgent alerts are held until strong coverage — then released in a controlled, staggered cascade.",
            },
            {
              icon: "⚡",
              title: "Real-Time Zone Classification",
              desc: "Every 100m segment is classified as Green, Yellow, or Red based on predicted connectivity.",
            },
            {
              icon: "🔄",
              title: "Mid-Route Auto-Switch",
              desc: "Automatically re-routes to a better-connected alternative when a dead zone is detected ahead.",
            },
            {
              icon: "📊",
              title: "ETA vs Coverage Tradeoff",
              desc: "A continuous slider lets users balance speed against signal quality for their specific needs.",
            },
          ].map((f) => (
            <div key={f.title} className="landing-feature-card">
              <span className="landing-feature-icon">{f.icon}</span>
              <h3 className="landing-feature-title">{f.title}</h3>
              <p className="landing-feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── How It Works ─── */}
      <section id="how-it-works" className="landing-section">
        <h2 className="landing-section-title">How it works</h2>
        <div className="landing-steps">
          {[
            { step: "01", title: "Build a Corridor", desc: "Enter origin and destination. We fetch real road routes and overlay cell tower data." },
            { step: "02", title: "Score Every Segment", desc: "Each 100m stretch is scored by tower density, radio technology, and signal samples." },
            { step: "03", title: "Rank & Recommend", desc: "Routes are ranked by a blend of ETA and connectivity — with weak-zone penalties applied." },
            { step: "04", title: "Drive with Intelligence", desc: "During playback, notifications are filtered by zone and released in controlled cascades." },
          ].map((s) => (
            <div key={s.step} className="landing-step">
              <span className="landing-step-num">{s.step}</span>
              <div>
                <h3 className="landing-step-title">{s.title}</h3>
                <p className="landing-step-desc">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="landing-cta-section">
        <h2 className="landing-cta-title">Ready to explore?</h2>
        <p className="landing-cta-subtitle">See connectivity-aware routing in action with our interactive demo.</p>
        <Link href="/dashboard" className="landing-btn-primary" style={{ fontSize: "1rem", padding: "14px 36px" }}>
          Launch Dashboard
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ marginLeft: 8 }}>
            <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>
      </section>

      {/* ─── Footer ─── */}
      <footer className="landing-footer">
        <span>Node Zero — MAHE Hackathon Finale 2026</span>
      </footer>

      <style>{`
        .landing-root {
          min-height: 100vh;
          background: var(--surface);
          color: var(--text-primary);
          overflow-x: hidden;
        }

        /* ─── Nav ─── */
        .landing-nav {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 50;
          background: var(--card);
          backdrop-filter: blur(16px);
          -webkit-backdrop-filter: blur(16px);
          border-bottom: 1px solid var(--border);
        }
        .landing-nav-inner {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 32px;
          height: 64px;
          display: flex;
          align-items: center;
          justify-content: space-between;
        }
        .landing-logo {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .landing-logo-text {
          font-family: "Sora", sans-serif;
          font-size: 1.25rem;
          font-weight: 700;
          letter-spacing: -0.02em;
        }
        .landing-nav-links {
          display: flex;
          align-items: center;
          gap: 24px;
        }
        .landing-link {
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--text-muted);
          text-decoration: none;
          transition: color 200ms;
        }
        .landing-link:hover { color: var(--text-primary); }

        /* ─── Hero ─── */
        .landing-hero {
          max-width: 1200px;
          margin: 0 auto;
          padding: 120px 32px 80px;
        }
        .landing-hero-content {
          display: flex;
          align-items: center;
          gap: 48px;
        }
        .landing-hero-left {
          flex: 1;
          min-width: 0;
        }
        .landing-hero-right {
          flex: 0 0 480px;
          max-width: 480px;
        }
        .landing-globe {
          width: 100%;
          filter: drop-shadow(0 20px 60px rgba(0, 0, 0, 0.15));
        }

        .landing-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          font-size: 0.75rem;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 20px;
        }
        .landing-badge-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #2d965d;
          animation: pulse-soft 2.4s ease infinite;
        }

        .landing-title {
          font-family: "Sora", sans-serif;
          font-size: clamp(3rem, 6vw, 5.5rem);
          font-weight: 800;
          letter-spacing: -0.04em;
          line-height: 1.05;
          margin: 0 0 24px;
        }
        .landing-subtitle {
          font-size: 1.15rem;
          line-height: 1.7;
          color: var(--text-muted);
          max-width: 520px;
          margin: 0 0 36px;
        }

        .landing-cta-row {
          display: flex;
          gap: 14px;
          margin-bottom: 48px;
        }
        .landing-btn-primary {
          display: inline-flex;
          align-items: center;
          padding: 12px 28px;
          background: var(--text-primary);
          color: var(--surface);
          font-size: 0.9rem;
          font-weight: 600;
          border-radius: 12px;
          text-decoration: none;
          transition: transform 150ms, box-shadow 150ms;
          border: none;
          cursor: pointer;
        }
        .landing-btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        }
        .landing-btn-secondary {
          display: inline-flex;
          align-items: center;
          padding: 12px 28px;
          background: transparent;
          color: var(--text-primary);
          font-size: 0.9rem;
          font-weight: 600;
          border-radius: 12px;
          text-decoration: none;
          border: 1px solid var(--border);
          transition: border-color 200ms, background 200ms;
          cursor: pointer;
        }
        .landing-btn-secondary:hover {
          border-color: var(--text-muted);
          background: var(--card);
        }

        .landing-stats {
          display: flex;
          align-items: center;
          gap: 28px;
        }
        .landing-stat { text-align: center; }
        .landing-stat-value {
          display: block;
          font-family: "Sora", sans-serif;
          font-size: 1.6rem;
          font-weight: 700;
          letter-spacing: -0.02em;
        }
        .landing-stat-label {
          display: block;
          font-size: 0.7rem;
          font-weight: 500;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.06em;
          margin-top: 2px;
        }
        .landing-stat-divider {
          width: 1px;
          height: 36px;
          background: var(--border);
        }

        /* ─── Sections ─── */
        .landing-section {
          max-width: 1200px;
          margin: 0 auto;
          padding: 80px 32px;
        }
        .landing-section-title {
          font-family: "Sora", sans-serif;
          font-size: 2rem;
          font-weight: 700;
          letter-spacing: -0.03em;
          text-align: center;
          margin: 0 0 48px;
        }

        /* ─── Features Grid ─── */
        .landing-features-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
        }
        .landing-feature-card {
          padding: 28px;
          border-radius: 16px;
          border: 1px solid var(--border);
          background: var(--card);
          transition: transform 200ms, box-shadow 200ms;
        }
        .landing-feature-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--shadow-soft);
        }
        .landing-feature-icon {
          font-size: 1.5rem;
          display: block;
          margin-bottom: 12px;
        }
        .landing-feature-title {
          font-family: "Sora", sans-serif;
          font-size: 1rem;
          font-weight: 600;
          margin: 0 0 8px;
        }
        .landing-feature-desc {
          font-size: 0.85rem;
          line-height: 1.6;
          color: var(--text-muted);
          margin: 0;
        }

        /* ─── Steps ─── */
        .landing-steps {
          max-width: 640px;
          margin: 0 auto;
          display: flex;
          flex-direction: column;
          gap: 32px;
        }
        .landing-step {
          display: flex;
          gap: 20px;
          align-items: flex-start;
        }
        .landing-step-num {
          font-family: "Sora", sans-serif;
          font-size: 2rem;
          font-weight: 800;
          color: var(--border);
          line-height: 1;
          min-width: 48px;
        }
        .landing-step-title {
          font-family: "Sora", sans-serif;
          font-size: 1.05rem;
          font-weight: 600;
          margin: 0 0 6px;
        }
        .landing-step-desc {
          font-size: 0.85rem;
          line-height: 1.6;
          color: var(--text-muted);
          margin: 0;
        }

        /* ─── CTA ─── */
        .landing-cta-section {
          text-align: center;
          padding: 80px 32px;
        }
        .landing-cta-title {
          font-family: "Sora", sans-serif;
          font-size: 2.2rem;
          font-weight: 700;
          letter-spacing: -0.03em;
          margin: 0 0 12px;
        }
        .landing-cta-subtitle {
          font-size: 1.05rem;
          color: var(--text-muted);
          margin: 0 0 32px;
        }

        /* ─── Footer ─── */
        .landing-footer {
          text-align: center;
          padding: 32px;
          font-size: 0.75rem;
          color: var(--text-muted);
          border-top: 1px solid var(--border);
        }

        /* ─── Responsive ─── */
        @media (max-width: 900px) {
          .landing-hero-content { flex-direction: column-reverse; gap: 32px; }
          .landing-hero-right { flex: none; max-width: 320px; width: 100%; }
          .landing-features-grid { grid-template-columns: 1fr; }
          .landing-stats { flex-wrap: wrap; justify-content: center; }
          .landing-nav-links .landing-link { display: none; }
        }
      `}</style>
    </div>
  );
}
