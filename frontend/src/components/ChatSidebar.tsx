"use client";

import { useState, type FormEvent } from "react";

export type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

export function ChatSidebar({
  messages,
  onSend,
  loading,
}: {
  messages: ChatMessage[];
  onSend: (message: string) => Promise<void>;
  loading: boolean;
}) {
  const [draft, setDraft] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed) return;
    setDraft("");
    await onSend(trimmed);
  };

  return (
    <aside className="rounded-[32px] border border-[var(--stroke)] bg-white/95 p-6 shadow-[var(--shadow)]">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
            AI advisor
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--navy-dark)]">
            Board assistant
          </h2>
        </div>
        <span className="rounded-full bg-[var(--accent-yellow)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.25em] text-navy-dark">
          Fast replies
        </span>
      </div>

      <div className="space-y-4 overflow-y-auto border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 max-h-[520px] rounded-3xl">
        {messages.length === 0 ? (
          <p className="text-slate-500">
            Ask the AI for a board suggestion, a task summary, or a card rewrite.
          </p>
        ) : (
          messages.map((message, index) => (
            <div key={`${message.role}-${index}`}>
              <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-slate-500">
                <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
                {message.role === "user" ? "You" : "Assistant"}
              </div>
              <div className="rounded-3xl bg-white px-4 py-3 shadow-sm">
                <p className="whitespace-pre-wrap text-sm leading-6 text-slate-800">
                  {message.text}
                </p>
              </div>
            </div>
          ))
        )}
      </div>

      <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700" htmlFor="ai-prompt">
          Ask the board assistant
        </label>
        <textarea
          id="ai-prompt"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          rows={4}
          className="w-full rounded-3xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
          placeholder="Summarize the board, create tasks, or suggest updates..."
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-[var(--primary-blue)] px-4 py-3 text-sm font-semibold text-white transition hover:bg-sky-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Thinking..." : "Send to AI"}
        </button>
      </form>
    </aside>
  );
}
