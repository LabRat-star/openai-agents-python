import React, { useState } from "react";

export default function ChatWindow({ apiBase }: { apiBase: string }) {
  const [messages, setMessages] = useState<{ from: string; text: string }[]>([]);
  const [input, setInput] = useState("");

  async function send() {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setMessages((m) => [...m, { from: "user", text: userMsg }]);
    setInput("");
    try {
      const res = await fetch(`${apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { from: "bot", text: data.reply }]);
    } catch (e) {
      setMessages((m) => [...m, { from: "bot", text: "Error contacting API." }]);
    }
  }

  return (
    <div style={{ maxWidth: 720 }}>
      <div style={{ border: "1px solid #ddd", padding: 12, minHeight: 240 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ margin: "8px 0" }}>
            <strong>{m.from}:</strong> <span>{m.text}</span>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          style={{ flex: 1, padding: 8 }}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Type a message..."
        />
        <button onClick={send} style={{ padding: "8px 12px" }}>
          Send
        </button>
      </div>
    </div>
  );
}
