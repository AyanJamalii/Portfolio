import Image from "next/image";

const socialLinks = [
  {
    name: "Github",
    url: "https://github.com/ayanjamali",
    icon: "/github.webp",
  },
  {
    name: "Gmail",
    url: "mailto:here.ayanjamali@gmail.com",
    icon: "/gmail.webp",
  },
  {
    name: "LinkedIn",
    url: "https://linkedin.com/in/ayanjamali",
    icon: "/LinkedIn.webp",
  },
  {
    name: "Discord",
    url: "https://discord.com",
    icon: "/discord.webp",
  },
];

export default function ConnectSection() {
  return (
    <section className="content-section connect-section">
      <div className="connect-container">
        
        <div className="connect-left">
          <span className="connect-kicker">/ Get In Touch</span>
          <h2 className="connect-title">Let&apos;s Connect?</h2>
          <p className="connect-desc">
            Got a project in mind, an AI workflow to build, you can usually find me lurking on GitHub looking at commits, hanging out on Discord, or sharing visual explorations. For work inquiries, slide into my LinkedIn or drop a good old Gmail.
          </p>
          <a
            href="mailto:here.ayanjamali@gmail.com"
            className="connect-action-btn"
          >
            Let&apos;s build ↗
          </a>
        </div>

        <div className="connect-grid">
          {socialLinks.map((item) => (
            <a 
              key={item.name}
              href={item.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="connect-card"
            >
              <div className="connect-icon-wrapper">
                <Image 
                  src={item.icon} 
                  alt={item.name} 
                  width={24} 
                  height={24} 
                  className="connect-logo-img"
                />
              </div>
              <div>
                <strong className="connect-card-title">{item.name}</strong>
              </div>
            </a>
          ))}
        </div>

      </div>
    </section>
  );
}