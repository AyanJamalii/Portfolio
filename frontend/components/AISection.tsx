"use client";
import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from "react-markdown";

export default function AISection() {
    const [message, setMessage] = useState("");
    const [threadId] = useState(() => crypto.randomUUID());
    const [messages, setMessages] = useState<{role: "user" | "assistant"; content: string}[]>([
        {
            role: "assistant",
            content: "Hi, I'm Ayan AI. Ask me anything about Ayan's Skills, education, learning or professional Experience or just Schedule a meeting with him."
        },
    ]);

    const [isLoading, setIsLoading] = useState(false);

    const messagesRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const el = messagesRef.current;
        if (!el) return;
        el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }, [messages, isLoading]);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Grow the box with the text (up to the CSS max-height), shrink back after sending
    useEffect(() => {
        const el = inputRef.current;
        if (!el) return;
        el.style.height = "auto";
        el.style.height = `${el.scrollHeight}px`;
    }, [message]);

    // Put the cursor back in the box after Ayan AI replies
    useEffect(() => {
        if (!isLoading && messages.length > 1) {
            inputRef.current?.focus({ preventScroll: true });
        }
    }, [isLoading, messages.length]);
    
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

function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }
}


return (
    <section id="ai" className="ai-section">
      <div className="ai-intro">
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

        <div className="ai-messages" ref={messagesRef}>
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
          <textarea
            ref={inputRef}
            rows={1}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about Ayan..."
            aria-label="Ask Ayan AI"
            enterKeyHint="send"
            maxLength={2000}
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