import React from "react";
import ChatWindow from "../components/ChatWindow";

export default function Home() {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  return (
    <main style={{ padding: 20, fontFamily: "system-ui, sans-serif" }}>
      <h1>Chat (minimal)</h1>
      <ChatWindow apiBase={apiBase} />
    </main>
  );
}
