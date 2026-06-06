"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, User, Bot, Loader2 } from "lucide-react";

// Define our message structure natively
type Message = {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input;
    setInput("");
    setIsLoading(true);

    // 1. Add User Message to UI instantly
    const newUserMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
    };
    const newMessages = [...messages, newUserMsg];
    setMessages(newMessages);

    try {
      // 2. Initiate Native Fetch request to FastAPI
      const response = await fetch(
        `http://localhost:8000/api/${process.env.VAPI_SECRET}/chat/completions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: newMessages }),
        },
      );

      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      if (!response.body) throw new Error("No response body available");

      // 3. Add a blank Assistant Message placeholder to the UI
      const assistantMsgId = (Date.now() + 1).toString();
      setMessages((prev) => [
        ...prev,
        { id: assistantMsgId, role: "assistant", content: "" },
      ]);

      // 4. Set up the Native Stream Reader
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;

      // 5. Read chunks as they arrive from the network
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;

        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          // SSE payloads are separated by double newlines
          const lines = chunk.split("\n\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              const dataStr = line.substring(6); // Remove 'data: ' prefix

              if (dataStr === "[DONE]") break; // End of stream marker

              try {
                // Parse the JSON payload from FastAPI/Groq
                const parsed = JSON.parse(dataStr);
                const textDelta = parsed.choices[0]?.delta?.content || "";

                if (textDelta) {
                  // Append the new text chunk to the current assistant message
                  setMessages((prev) => {
                    const updated = [...prev];
                    const lastIndex = updated.length - 1;
                    updated[lastIndex] = {
                      ...updated[lastIndex],
                      content: updated[lastIndex].content + textDelta,
                    };
                    return updated;
                  });
                }
              } catch (parseError) {
                console.error(
                  "Error parsing stream chunk:",
                  parseError,
                  "Raw chunk:",
                  dataStr,
                );
              }
            }
          }
        }
      }
    } catch (error) {
      console.error("Chat Error:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content:
            "Sorry, I encountered a network error while trying to respond.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center shadow-sm z-10">
        <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-lg mr-4 shadow-sm">
          YA
        </div>
        <div>
          <h1 className="font-bold text-xl leading-tight">Yawar Abass AI</h1>
          <p className="text-sm text-gray-500">AI Engineer Persona</p>
        </div>
      </header>

      {/* Chat History */}
      <main className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
            <Bot size={48} className="text-gray-300" />
            <p className="text-center max-w-sm">
              Hi, I'm Yawar's AI representative. Ask me about my background,
              high-performance web architectures, or let's book an interview!
            </p>
          </div>
        )}

        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`flex max-w-[80%] ${m.role === "user" ? "flex-row-reverse" : "flex-row"} items-end gap-2`}
            >
              {/* Avatar */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${m.role === "user" ? "bg-gray-800 text-white" : "bg-blue-100 text-blue-600"}`}
              >
                {m.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>

              {/* Message Bubble */}
              <div
                className={`px-4 py-3 rounded-2xl shadow-sm ${m.role === "user" ? "bg-gray-800 text-white rounded-br-none" : "bg-white border border-gray-100 text-gray-800 rounded-bl-none"}`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>
              </div>
            </div>
          </div>
        ))}

        {/* Initial Loading Indicator (Before first token arrives) */}
        {isLoading && messages[messages.length - 1]?.role === "user" && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 max-w-[80%]">
              <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                <Bot size={16} />
              </div>
              <div className="px-4 py-3 rounded-2xl bg-white border border-gray-100 shadow-sm rounded-bl-none flex items-center">
                <Loader2 size={16} className="animate-spin text-gray-400" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t border-gray-200 p-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex gap-2 relative">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about my projects, stack, or book a meeting..."
              className="flex-1 rounded-full border border-gray-300 px-6 py-4 pr-14 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm transition-all"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="absolute right-2 top-2 bottom-2 aspect-square bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-full flex items-center justify-center transition-colors"
            >
              <Send size={18} />
            </button>
          </form>
          <div className="text-center mt-2">
            <span className="text-xs text-gray-400">
              Custom Built SSE Parser | FastAPI Backend
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
