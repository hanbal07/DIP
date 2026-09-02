"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Bot, User, Sparkles, Plus, FileText, MessagesSquare } from "lucide-react";
import { chatApi, ApiError } from "@/lib/api";
import type { ChatResponse, ConversationOut, MessageOut } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";

interface ChatPanelProps {
  documentId?: string;
  conversations: ConversationOut[];
  onConversationCreated?: (c: ConversationOut) => void;
}

const DOC_SUGGESTIONS = ["Summarize this document", "List the key financial figures", "What are the main clauses or terms?"];
const GLOBAL_SUGGESTIONS = ["What documents do I have?", "Summarize the latest uploads", "Compare key figures across documents"];

export function ChatPanel({
  documentId,
  conversations,
  onConversationCreated,
}: ChatPanelProps) {
  const { toast } = useToast();
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [citations, setCitations] = useState<ChatResponse["citations"]>([]);
  const [answerMeta, setAnswerMeta] = useState<Pick<ChatResponse, "has_sufficient_evidence" | "model"> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setConversationId(conversations[0]?.id ?? null);
  }, [conversations]);

  useEffect(() => {
    if (conversationId) {
      chatApi
        .messages(conversationId)
        .then((msgs) => {
          setMessages(msgs);
          setCitations([]);
        })
        .catch(() => undefined);
    } else {
      setMessages([]);
      setCitations([]);
    }
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, citations, loading]);

  async function send(text?: string) {
    const q = (text ?? question).trim();
    if (!q || loading) return;
    setLoading(true);
    setCitations([]);
    setAnswerMeta(null);
    try {
      const resp = await chatApi.chat({
        question: q,
        conversation_id: conversationId ?? undefined,
        document_ids: documentId ? [documentId] : undefined,
      });
      const isNew = !conversations.some((c) => c.id === resp.conversation_id);
      if (isNew && onConversationCreated) {
        onConversationCreated({
          id: resp.conversation_id,
          document_id: documentId ?? null,
          title: q.slice(0, 100),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }
      setConversationId(resp.conversation_id);
      setMessages((prev) => [
        ...prev,
        { id: "u-" + Date.now(), role: "user", content: q, created_at: new Date().toISOString(), citations: [] },
        {
          id: "a-" + Date.now(),
          role: "assistant",
          content: resp.answer,
          created_at: new Date().toISOString(),
          citations: [],
        },
      ]);
      setCitations(resp.citations);
      setAnswerMeta({ has_sufficient_evidence: resp.has_sufficient_evidence, model: resp.model ?? null });
      setQuestion("");
    } catch (err) {
      toast("error", err instanceof ApiError ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  }

  const suggestions = documentId ? DOC_SUGGESTIONS : GLOBAL_SUGGESTIONS;

  return (
    <div className="flex h-full flex-col gap-3">
      {/* Conversation switcher */}
      {conversations.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-b border-border pb-2">
          <Button
            variant={conversationId === null ? "secondary" : "ghost"}
            size="sm"
            className={cn("gap-1 text-xs", conversationId === null && "font-medium")}
            onClick={() => setConversationId(null)}
          >
            <Plus className="size-3.5" />
            New chat
          </Button>
          <div className="flex flex-1 flex-wrap gap-1.5">
            {conversations.map((c) => (
              <Button
                key={c.id}
                variant={conversationId === c.id ? "secondary" : "ghost"}
                size="sm"
                className="max-w-[180px] gap-1 text-xs"
                onClick={() => setConversationId(c.id)}
              >
                <MessagesSquare className="size-3 shrink-0 text-muted-foreground" />
                <span className="truncate">{c.title?.slice(0, 24)}</span>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Message list */}
      <div className="flex-1 space-y-4 overflow-y-auto pr-1" aria-live="polite">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 py-8 text-center">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Sparkles className="size-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                {documentId ? "Ask about this document" : "Ask across all your documents"}
              </p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Answers are grounded in extracted content and include citations to source pages.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground shadow-sm transition-[color,border-color,transform] hover:border-primary/30 hover:text-foreground active:scale-95"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble key={m.id} message={m} isNew={i >= messages.length - 2 && loading} />
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Spinner className="size-3.5" />
            Reasoning with sources…
          </div>
        )}

        {citations.length > 0 && (
          <div className="animate-fade-in rounded-lg border border-border bg-card p-3 shadow-sm">
            <div className="mb-2 flex items-center justify-between">
              <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                <FileText className="size-3.5" />
                Sources cited
              </p>
              {answerMeta && (
                <span className="text-[10px] text-muted-foreground">
                  {answerMeta.model ? `${answerMeta.model} · ` : ""}
                  {answerMeta.has_sufficient_evidence ? "cited evidence" : "limited evidence"}
                </span>
              )}
            </div>
            <ul className="space-y-1.5">
              {citations.map((c, i) => (
                <li key={i} className="text-xs">
                  <span className="inline-flex items-center gap-1 font-medium text-primary">
                    {c.document_filename} <span className="text-muted-foreground">· p{c.page_number} · {Math.round(c.score * 100)}%</span>
                  </span>
                  <span className="block text-muted-foreground">
                    {c.snippet.slice(0, 160)}
                    {c.snippet.length > 160 ? "…" : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="flex items-end gap-2 border-t border-border pt-3">
        <Textarea
          placeholder={documentId ? "Ask about this document…" : "Ask across all documents…"}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          aria-label="Your question"
          className="max-h-32 min-h-[44px]"
        />
        <Button onClick={() => send()} disabled={loading || !question.trim()} aria-label="Send question" className="h-11 shrink-0">
          {loading ? <Spinner className="size-4" /> : <Send className="size-4" />}
        </Button>
      </div>
    </div>
  );
}

function MessageBubble({ message, isNew }: { message: MessageOut; isNew: boolean }) {
  const isUser = message.role === "user";
  return (
    <div
      className={cn(
        "flex items-start gap-2.5 animate-fade-in",
        isUser && "flex-row-reverse"
      )}
    >
      <div
        className={cn(
          "flex size-7 shrink-0 items-center justify-center rounded-full text-primary-foreground",
          isUser ? "bg-primary" : "bg-muted-foreground/15 text-muted-foreground"
        )}
      >
        {isUser ? <User className="size-3.5" /> : <Bot className="size-3.5" />}
      </div>
      <div
        className={cn(
          "max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm shadow-sm",
          isUser
            ? "rounded-tr-sm bg-primary text-primary-foreground"
            : "rounded-tl-sm border border-border bg-card text-foreground"
        )}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        {!isUser && (message.citations?.length ?? 0) > 0 && (
          <div className="mt-2 flex flex-wrap gap-1 border-t border-border pt-2">
            {(message.citations as unknown as ChatResponse["citations"]).map((c, i) => (
              <Badge key={i} variant="outline" className="text-[10px]">
                {c.document_filename} · p{c.page_number}
              </Badge>
            ))}
          </div>
        )}
      </div>
      {isNew && <span className="sr-only">New message</span>}
    </div>
  );
}