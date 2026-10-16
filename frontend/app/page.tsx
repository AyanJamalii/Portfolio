"use client";

import { useEffect, useState } from "react";
import Image from 'next/image'
import { Mail, } from "lucide-react";
import FolderFloat from "@/components/FolderFloat";
import AISection from "@/components/AISection";
import ConnectSection from "@/components/ConnectSection";

const skills = [
  "HTML",
  "CSS",
  "JavaScript",
  "React",
  "Next.js",
  "TypeScript",
  "Python",
  "LangChain",
  "LangGraph",
  "RAG",
  "Gemini API",
  "OpenAI API",
  "Git",
  "GitHub",
  "Tailwind CSS",
  "Figma",
];

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
    title: "RAG Prompt Architecture",
    description:
      "Building structured AI systems with retrieval, context and reliable prompting.",
  },
];

const projects = [
  {
    title: "Ayan Portfolio & Personal AI Agent",
    date: "September 2026 – Present",
    stack: ["Python", "LangGraph", "FastAPI", "React", "Next.js", "Gemini API"],
    description:
      "An interactive portfolio powered by a custom LangGraph backend agent that answers questions about Muhammad Ayan's professional background, skills, and projects.",
    highlight:
      "Integrated custom conversational AI agent with real-time streaming and robust frontend-backend integration.",
    github: "",
    live: "https://meetayan.vercel.app",
  },
  {
    title: "MediCare Clinic & Voice Appointment Agent",
    date: "August 2026 – September 2026",
    stack: ["React", "FastAPI", "LangChain", "Web Speech API", "Gemini API"],
    description:
      "A specialized healthcare clinic website featuring an interactive chat and voice agent capable of answering doctor inquiries and seamlessly scheduling appointments.",
    highlight:
      "Integrated dual-channel voice and chat AI pipeline for frictionless patient appointment booking.",
    github: "",
    live: "",
  },
  {
    title: "Legal & HR Document Q&A RAG Agent",
    date: "July 2026 – August 2026",
    stack: ["Next.js", "FastAPI", "LangChain RAG", "ChromaDB", "Gemini Embeddings"],
    description:
      "A corporate dashboard allowing users to upload business contracts and HR policies, utilizing a vector database and RAG architecture to extract precise answers and summaries.",
    highlight:
      "Sub-second contextual indexing and strict document grounding to eliminate AI hallucinations.",
    github: "",
    live: "",
  },
  {
    title: "Real Estate Lead Qualification & Tour Bot",
    date: "June 2026 – July 2026",
    stack: ["React", "Tailwind CSS", "LangGraph", "FastAPI", "OpenAI/Gemini API"],
    description:
      "A property listing web application equipped with a multi-step LangGraph conversational agent that qualifies buyers, shares property specs, and coordinates property tours.",
    highlight:
      "Automated multi-step buyer qualification and interactive tour scheduling workflows.",
    github: "",
    live: "",
  },
];

export default function Home() {
    useEffect(() => {
  console.log("AYAN PORTFOLIO CLIENT JS IS RUNNING");
}, []);
  const [activeTab, setActiveTab] = useState<"projects" | "about">(
    "projects"
  );

  const [activeHeroPoint, setActiveHeroPoint] = useState(0);



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
  const handleScroll = () => {
    const projectsSection = document.getElementById("projects");
    const aboutSection = document.getElementById("about");

    if (!projectsSection || !aboutSection) return;

    const scrollPosition = window.scrollY + 150;

    const projectsTop = projectsSection.offsetTop;
    const aboutTop = aboutSection.offsetTop;

    if (scrollPosition >= aboutTop) {
      setActiveTab("about");
    } else {
      setActiveTab("projects");
    }
  };

  window.addEventListener("scroll", handleScroll);

  handleScroll();

  return () => {
    window.removeEventListener("scroll", handleScroll);
  };
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
          Ayan    J.
        </a>

        <button
          className="nav-cta"
          onClick={() =>
            document.getElementById("contact")?.scrollIntoView({
              behavior: "smooth",
            })
          }
        >
            Let&apos;s Talk
            <Mail size={16} strokeWidth={1.8} />
        </button>
      </header>

      {/* hero */}

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

            <div className="hero-person">
              <Image
                src="/portrait.webp"
                alt="Ayan"
                width={500}
                height={500}
                className="portrait"               />
            </div>

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
                 Let&apos;s Talk <Mail size={16} strokeWidth={1.8} />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* nav */}

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

      {/* projects */}

      <section id="projects" className="content-section projects-section">
        <div className="section-heading">
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
                  {index === 0 ? (
                    <a
                      href="#ai"
                      onClick={(e) => {
                        e.preventDefault();
                        document.getElementById("ai")?.scrollIntoView({
                          behavior: "smooth",
                          block: "start",
                        });
                      }}
                    >
                      Talk ↗
                    </a>
                  ) : (
                    <a href={project.live}>Visit Site ↗</a>
                  )}
                  <a href={project.github}>◉ View on Github</a>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* about */}

      <section id="about" className="content-section about-section">
        <div className="section-heading">
          <span>/ Get to know me</span>
          <h2>About</h2>
        </div>

        <div className="about-grid">
          <div>
            <p className="about-large">
              Hi, I&apos;m Ayan, a 19-year-old Computer Science student and aspiring AI Engineer. I build minimal frontend interfaces and orchestrate Gen AI &amp; Agentic AI workflows, exploring how intelligent code makes the web feel seamless.
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

  <div className="about-skills">
    <FolderFloat
      className="about-folder"
      items={skills}
      label="My Skills"
      sublabel={`${skills.length} skills`}
      trigger="hover"
      closeOnSelect
      physics
      drift={0.5}
      folderColor="#3f3f46"
      frontColor="#52525b"
      paperColor="#f5f5f5"
      itemColor="#f5f5f5"
      itemTextColor="#18181b"
      labelColor="#f5f5f5"
      width={200}
      height={148}
      radius={14}
      spread={180}
      lift={26}
      tilt={8}
      flapAngle={34}
      restAngle={16}
      openDuration={520}
      stagger={45}
      bounce={0.3}
    />
  </div>
</div>
        </div>
      </section>

      {/* ai */}

      <AISection />

      {/* connect */}

      <ConnectSection />

      {/* footer */}

      <footer className="footer">
        <span>© 2026 Ayan J. All rights reserved |  Your friendly neighborhood developer. :)</span>
      </footer>
    </main>
  );
}