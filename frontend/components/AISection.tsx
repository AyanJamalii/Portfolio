"use client";
import { useState } from 'react'
import ReactMarkdown from "react-markdown";

export default function AISection() {
    const [message, setMessage] = useState("");
    const [threadId] = useState(() => crypto.randomUUID());
    const [messages, setMessages] = useState<{role: "user" | "assistant"; content: string}[]>([
        {
            role: "assistant",
            content: "Hi, I'm Ayan AI. Ask me anything about Ayan's Skills, education, learning or professional Experience."
        },
    ]);

    const [isLoading, setIsLoading] = useState(false);
    
async function handleSubmit(
  event: React.SubmitEvent<HTMLFormElement>
) {
  event.preventDefault();


  const trimmedMessage = message.trim();

  if (!trimmedMessage || isLoading) return;

  setMessages((current) => [
    ...current,
    {
      role: "user",
      content: trimmedMessage,
    },
  ]);

  setMessage("");
  setIsLoading(true);

  try {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
    
    const response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: trimmedMessage,
        thread_id: threadId,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to get AI response.");
    }

    const data = await response.json();

    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: data.response,
      },
    ]);
  } catch (error) {
    console.error("AI chat error:", error);

    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: "I couldn't connect to Ayan AI right now. Please try again.",
      },
    ]);
  } finally {
    setIsLoading(false);
  }
}
return (
    <section id="ai" className="ai-section">
      <div className="ai-intro">
        <span className="ai-kicker">/ Interactive Persona</span>

        <h2>
          Know more
          <br />
          about me.
        </h2>

        <p>
          Curious about my work, skills, education or AI engineering journey?
          Ask Ayan AI and explore my professional profile through conversation.
        </p>
      </div>

      <div className="ai-chat">
        <div className="ai-chat-header">
          <div>
            <span className="ai-status">
              <span className="ai-status-dot" />
              Ayan AI
            </span>

            <span className="ai-status-text">Portfolio Assistant</span>
          </div>
        </div>

        <div className="ai-messages">
          {messages.map((item, index) => (
            <div
  key={`${item.role}-${index}`}
  className={`ai-message ${
    item.role === "user"
      ? "ai-message-user"
      : "ai-message-ai"
  }`}
>
  <ReactMarkdown>{item.content}</ReactMarkdown>
</div>
          ))}

          {isLoading && (
            <div className="ai-message ai-message-ai ai-typing">
              <span />
              <span />
              <span />
            </div>
          )}
        </div>

        <form className="ai-input-wrapper" onSubmit={handleSubmit}>
          <input
            type="text"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask anything about Ayan..."
            aria-label="Ask Ayan AI"
            disabled={isLoading}
          />

          <button
            type="submit"
            aria-label="Send message"
            disabled={!message.trim() || isLoading}
          >
            ↗
          </button>
        </form>
      </div>
    </section>
  );
}