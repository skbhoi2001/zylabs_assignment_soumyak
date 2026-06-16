import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Bot, User } from "lucide-react";
import { getChatHistory, sendChat } from "../api/client";

function Message({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${isUser ? "bg-indigo-100" : "bg-gray-100"}`}>
        {isUser ? <User className="w-4 h-4 text-indigo-600" /> : <Bot className="w-4 h-4 text-gray-600" />}
      </div>
      <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${isUser ? "bg-indigo-600 text-white rounded-tr-sm" : "bg-white border border-gray-200 text-gray-700 rounded-tl-sm"}`}>
        {msg.content}
      </div>
    </div>
  );
}

export default function ChatPanel({ sessionId, reportReady }) {
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);
  const qc = useQueryClient();

  const { data: messages = [] } = useQuery({
    queryKey: ["chat", sessionId],
    queryFn: () => getChatHistory(sessionId),
    refetchInterval: reportReady ? false : 5000,
  });

  const { mutate: send, isPending } = useMutation({
    mutationFn: (content) => sendChat(sessionId, content),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chat", sessionId] }),
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isPending) return;
    setInput("");
    send(trimmed);
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col h-[500px]">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-800">Follow-up Chat</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          {reportReady ? "Ask anything about the research report" : "Report still generating — you can ask general questions"}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-sm text-gray-400 mt-8">
            <Bot className="w-10 h-10 mx-auto mb-2 text-gray-200" />
            <p>No messages yet.</p>
            <p className="text-xs mt-1">Ask a question about the company research.</p>
          </div>
        )}
        {messages.map((m) => (
          <Message key={m.id} msg={m} />
        ))}
        {isPending && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center">
              <Bot className="w-4 h-4 text-gray-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-2.5">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-100 flex gap-2">
        <input
          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-300 placeholder-gray-400"
          placeholder="Ask a question about the report…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isPending}
        />
        <button
          type="submit"
          disabled={isPending || !input.trim()}
          className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
