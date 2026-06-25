import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const FEATURES: { tag: string; title: string; desc: string }[] = [
  { tag: "01", title: "Image Enhancement", desc: "OpenCV preprocessing and restoration to recover detail from degraded forensic evidence." },
  { tag: "02", title: "Super Resolution", desc: "Real-ESRGAN and bicubic upscaling to reconstruct high-resolution imagery from low-quality sources." },
  { tag: "03", title: "Blur Detection", desc: "Automated sharpness analysis that flags motion and out-of-focus regions before enhancement." },
  { tag: "04", title: "Image Comparison", desc: "Interactive side-by-side and split-slider comparison of original and enhanced output." },
  { tag: "05", title: "Quality Metrics", desc: "Objective scoring with PSNR, SSIM, LPIPS, OCR confidence and face-similarity proxies." },
  { tag: "06", title: "Batch Experiments", desc: "Run reproducible benchmarks across models and datasets for research evaluation." },
  { tag: "07", title: "Report Generation", desc: "Export structured reports and CSV result sets for documentation and review." },
  { tag: "08", title: "Case Management", desc: "Organize evidence into investigation cases with a clear, auditable workflow." },
];

const WORKFLOW: { step: string; title: string; desc: string }[] = [
  { step: "1", title: "Upload Evidence", desc: "Add images to a case" },
  { step: "2", title: "Analyze Quality", desc: "Detect blur & baseline metrics" },
  { step: "3", title: "Enhance Image", desc: "Apply AI super-resolution" },
  { step: "4", title: "Compare Results", desc: "Inspect before & after" },
  { step: "5", title: "Generate Report", desc: "Export findings & metrics" },
];

const TECH = ["React", "FastAPI", "Firebase", "PyTorch", "OpenCV", "Real-ESRGAN", "SQLAlchemy", "Docker"];

const HIGHLIGHTS: { title: string; desc: string }[] = [
  { title: "AI-Assisted Enhancement", desc: "Deep-learning super-resolution tuned for forensic imagery." },
  { title: "Objective Quality Metrics", desc: "Quantitative, reproducible scoring rather than subjective judgement." },
  { title: "Research Experiment Support", desc: "Batch evaluation pipeline for comparing models on datasets." },
  { title: "Report Generation", desc: "One-click export of reports and CSV results for documentation." },
  { title: "Secure Authentication", desc: "Firebase identity with JWT-protected backend routes." },
  { title: "Case-Based Workflow", desc: "Evidence grouped into structured, traceable investigation cases." },
];

export function LandingPage() {
  const { isAuthenticated } = useAuth();
  const launchTo = isAuthenticated ? "/dashboard" : "/login";

  return (
    <div className="landing">
      {/* A. HERO */}
      <section className="hero">
        <span className="section-label">Forensic Imaging Platform</span>
        <h1 className="hero-title">ForensicX</h1>
        <p className="hero-tagline">AI-Powered Forensic Image Enhancement &amp; Authenticity Analysis</p>
        <p className="hero-overview">
          ForensicX is a research-oriented platform for enhancing, analyzing and validating
          forensic imagery. It combines AI super-resolution with objective quality metrics
          and a case-based workflow to support investigative and academic analysis.
        </p>
        <div className="hero-cta-row">
          <Link className="cta cta-primary" to={launchTo}>Launch Application</Link>
          <a className="cta cta-secondary" href="#features">Explore Features</a>
        </div>
      </section>

      {/* B. FEATURE SHOWCASE */}
      <section id="features" className="landing-section">
        <span className="section-label">Capabilities</span>
        <h2 className="section-title">Feature Showcase</h2>
        <div className="feature-grid">
          {FEATURES.map((f) => (
            <article key={f.tag} className="card feature-card">
              <span className="feature-tag">[{f.tag}]</span>
              <h3 className="feature-title">{f.title}</h3>
              <p className="muted">{f.desc}</p>
            </article>
          ))}
        </div>
      </section>

      {/* C. WORKFLOW */}
      <section className="landing-section">
        <span className="section-label">Process</span>
        <h2 className="section-title">Investigation Workflow</h2>
        <div className="workflow">
          {WORKFLOW.map((w, i) => (
            <div className="workflow-item" key={w.step}>
              <div className="card workflow-card">
                <span className="workflow-step">{w.step}</span>
                <h3 className="feature-title">{w.title}</h3>
                <p className="muted">{w.desc}</p>
              </div>
              {i < WORKFLOW.length - 1 ? <span className="workflow-arrow">&rarr;</span> : null}
            </div>
          ))}
        </div>
      </section>

      {/* D. TECHNOLOGY STACK */}
      <section className="landing-section">
        <span className="section-label">Engineering</span>
        <h2 className="section-title">Technology Stack</h2>
        <div className="tech-grid">
          {TECH.map((t) => (
            <span key={t} className="tech-chip">{t}</span>
          ))}
        </div>
      </section>

      {/* E. PROJECT HIGHLIGHTS */}
      <section className="landing-section">
        <span className="section-label">Why ForensicX</span>
        <h2 className="section-title">Project Highlights</h2>
        <div className="highlight-grid">
          {HIGHLIGHTS.map((h) => (
            <article key={h.title} className="card highlight-card">
              <h3 className="feature-title">{h.title}</h3>
              <p className="muted">{h.desc}</p>
            </article>
          ))}
        </div>
      </section>

      {/* F. ACADEMIC PROJECT */}
      <section className="landing-section">
        <span className="section-label">Academic Project</span>
        <h2 className="section-title">About This Project</h2>
        <div className="card about-card">
          <p className="hint">
            ForensicX is a final-year academic project demonstrating an end-to-end, production-style
            system for forensic image enhancement and authenticity analysis. It integrates a modern
            React + TypeScript frontend with a FastAPI backend, deep-learning image models, and an
            objective evaluation pipeline suitable for research benchmarking.
          </p>
          <div className="about-meta">
            <div className="about-meta-item">
              <span className="metric-section-label">Scope</span>
              <span className="metric-value">Forensic Image AI</span>
            </div>
            <div className="about-meta-item">
              <span className="metric-section-label">Frontend</span>
              <span className="metric-value">React + TypeScript + Vite</span>
            </div>
            <div className="about-meta-item">
              <span className="metric-section-label">Backend</span>
              <span className="metric-value">FastAPI + SQLAlchemy</span>
            </div>
            <div className="about-meta-item">
              <span className="metric-section-label">AI / Vision</span>
              <span className="metric-value">PyTorch + OpenCV</span>
            </div>
          </div>
          <div className="hero-cta-row">
            <Link className="cta cta-primary" to={launchTo}>Launch Application</Link>
            <a className="cta cta-secondary" href="#features">Explore Features</a>
          </div>
        </div>
      </section>

      {/* G. FOOTER */}
      <footer className="landing-footer">
        <div className="landing-footer-brand">
          <span className="brand-title">ForensicX</span>
          <p className="muted">AI-Powered Forensic Image Enhancement &amp; Authenticity Analysis</p>
        </div>
        <nav className="landing-footer-nav">
          <Link className="nav-link" to={launchTo}>Launch</Link>
          <Link className="nav-link" to="/dashboard">Dashboard</Link>
          <Link className="nav-link" to="/experiments">Experiments</Link>
        </nav>
        <p className="muted landing-copyright">© {new Date().getFullYear()} ForensicX — Academic Project. For analytical support only.</p>
      </footer>
    </div>
  );
}
