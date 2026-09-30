"use client";

import { useEffect, useState } from "react";
import Image from 'next/image'

const heroPoints = [
  {
    number: "01",
    title: "Pixel-Perfect UI",
    description:
      "High-performance interfaces built with modern frontend systems, responsive layouts and thoughtful interactions.",
  },
  {
    number: "02",
    title: "Agentic AI Integration",
    description:
      "Custom LLM, LangChain and LangGraph workflows integrated into useful product experiences.",
  },
  {
    number: "03",
    title: "RAG / Prompt Architecture",
    description:
      "Building structured AI systems with retrieval, context and reliable prompting.",
  },
];

const projects = [
  {
    title: "Nexus AI — Agentic Workflow Automation Platform",
    date: "August 2026 – September 2026",
    stack: ["Next.js", "LangGraph", "Python", "Tailwind CSS", "Next.js"],
    description:
      "A visual workflow builder designed for developers to orchestrate multi-agent AI systems without complex boilerplate.",
    highlight:
      "Reduced workflow setup time by 80% with visual drag-and-drop node logic.",
    github: "#",
    live: "#",
  },
  {
    title: "OmniDocs — Semantic Knowledge Base & RAG Chat",
    date: "July 2026 – August 2026",
    stack: ["Next.js", "LangChain", "Python", "Tailwind CSS", "Next.js"],
    description:
      "An enterprise-grade document intelligence platform that transforms raw PDFs and documentation into interactive AI search interfaces.",
    highlight:
      "Sub-second contextual indexing with context-aware semantic retrieval.",
    github: "#",
    live: "#",
  },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<"projects" | "about">(
    "projects"
  );

  const [activeHeroPoint, setActiveHeroPoint] = useState(0);

  /*
   * HERO FEATURE AUTO ROTATION
   *
   * 01 → 02 → 03 → 01 ...
   */
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveHeroPoint((current) => (current + 1) % heroPoints.length);
    }, 3500);

    return () => clearInterval(interval);
  }, []);

  /*
   * PROJECT / ABOUT SCROLL SPY
   */
  useEffect(() => {
    const sections = ["projects", "about"];

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (visible[0]) {
          setActiveTab(visible[0].target.id as "projects" | "about");
        }
      },
      {
        rootMargin: "-25% 0px -55% 0px",
        threshold: [0.1, 0.25, 0.5],
      }
    );

    sections.forEach((id) => {
      const element = document.getElementById(id);

      if (element) {
        observer.observe(element);
      }
    });

    return () => observer.disconnect();
  }, []);

  const scrollToSection = (id: "projects" | "about") => {
    document.getElementById(id)?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  return (
    <main className="site-shell">

      <header className="navbar">
        <a href="#top" className="logo">
          Ayan J.
        </a>

        <button
          className="nav-cta"
          onClick={() =>
            document.getElementById("contact")?.scrollIntoView({
              behavior: "smooth",
            })
          }
        >
          Let&apos;s Talk <span>↗</span>
        </button>
      </header>

      {/* ================= HERO ================= */}

      <section id="top" className="hero">
        <div className="hero-glow" />

        <div className="hero-content">
          <div className="hero-badges">
            <span>⌘ Code + Prompt</span>
            <span>☕ Powered by Coffee</span>
          </div>

          <h1>
            Hi I&apos;m Ayan
            <br />
            <span>AI Frontend Developer.</span>
          </h1>

          <div className="hero-grid">
            {/* LEFT HERO FEATURES */}

            <div className="hero-feature-wrapper">
              <div className="hero-feature-rail">
                <div
                  className="hero-feature-active"
                  style={{
                    transform: `translateY(${activeHeroPoint * 100}%)`,
                  }}
                />
              </div>

              <div className="hero-features">
                {heroPoints.map((point, index) => {
                  const isActive = index === activeHeroPoint;

                  return (
                    <button
                      key={point.number}
                      className={`hero-feature ${
                        isActive ? "hero-feature-active-text" : ""
                      }`}
                      onClick={() => setActiveHeroPoint(index)}
                    >
                      <span className="hero-feature-number">
                        {point.number} / {point.title}
                      </span>

                      <p>{point.description}</p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* CENTER PORTRAIT */}

            <div className="hero-person">
              <Image
                src="/portrait.png"
                alt="Ayan"
                width={500}
                height={500}
                className="portrait"               />
            </div>
            {/* RIGHT HERO COPY */}

            <div className="hero-side-copy hero-side-copy-right">
              <p>
                Crafting responsive, high-performance React & Next.js
                interfaces powered by intelligent AI agent backends. I care
                about clean systems, useful interactions and turning ideas
                into polished experiences.
              </p>

              <button
                className="hero-button"
                onClick={() =>
                  document.getElementById("contact")?.scrollIntoView({
                    behavior: "smooth",
                  })
                }
              >
                Let&apos;s Talk ↗
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ================= STICKY SECTION TABS ================= */}

      <nav className="section-tabs">
        <button
          className={activeTab === "projects" ? "active" : ""}
          onClick={() => scrollToSection("projects")}
        >
          Projects
        </button>

        <button
          className={activeTab === "about" ? "active" : ""}
          onClick={() => scrollToSection("about")}
        >
          About
        </button>
      </nav>

      {/* ================= PROJECTS ================= */}

      <section id="projects" className="content-section projects-section">
        <div className="section-heading">
          <span>Selected Work</span>
          <h2>Projects</h2>
        </div>

        <div className="projects-list">
          {projects.map((project, index) => (
            <article
              className={`project-card ${
                index % 2 === 1 ? "project-card-reverse" : ""
              }`}
              key={project.title}
            >
              <div className="project-image">
                <span>PROJECT 0{index + 1}</span>
              </div>

              <div className="project-info">
                <h3>{project.title}</h3>

                <p className="project-date">{project.date}</p>

                <div className="tech-list">
                  {project.stack.map((tech) => (
                    <span key={tech}>{tech}</span>
                  ))}
                </div>

                <div className="project-copy">
                  <strong>About Project:</strong>
                  <p>{project.description}</p>

                  <strong>Key Highlight:</strong>
                  <p>{project.highlight}</p>
                </div>

                <div className="project-actions">
                  <a href={project.live}>Visit Site ↗</a>
                  <a href={project.github}>◉ View on Github</a>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ================= ABOUT ================= */}

      <section id="about" className="content-section about-section">
        <div className="section-heading">
          <span>Get to know me</span>
          <h2>About</h2>
        </div>

        <div className="about-grid">
          <div>
            <p className="about-large">
              I&apos;m Ayan, a Computer Science student and aspiring AI
              Engineer focused on building thoughtful digital experiences.
            </p>
          </div>

          <div className="about-copy">
            <p>
              I started with frontend development and gradually moved deeper
              into Python, AI engineering, LangChain, LangGraph and RAG
              workflows.
            </p>

            <p>
              My current focus is combining polished interfaces with useful
              AI systems — creating products that feel simple on the surface
              while having powerful systems underneath.
            </p>

            <div className="about-details">
              <div>
                <span>Education</span>
                <strong>BS Computer Science</strong>
              </div>

              <div>
                <span>University</span>
                <strong>SSUET, Karachi</strong>
              </div>

              <div>
                <span>Focus</span>
                <strong>AI Engineering + Frontend</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= CONTACT ================= */}

      <section id="contact" className="contact-section">
        <div className="contact-glow" />

        <div className="contact-content">
          <span>Have an idea?</span>

          <h2>
            Let&apos;s build
            <br />
            something useful.
          </h2>

          <button className="contact-button">
            Start a conversation ↗
          </button>
        </div>
      </section>

      {/* ================= FOOTER ================= */}

      <footer className="footer">
        <span>© 2026 Ayan Jamali</span>
        <span>AI × Frontend</span>
      </footer>
    </main>
  );
}