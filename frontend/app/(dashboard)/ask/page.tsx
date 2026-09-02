"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { chatApi } from "@/lib/api";
import type { ConversationOut } from "@/lib/types";
import { PageHeader } from "@/components/page-header";
import { ChatPanel } from "@/components/chat-panel";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Reveal } from "@/components/motion/reveal";

export default function AskPage() {
  const [conversations, setConversations] = useState<ConversationOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    chatApi
      .conversations()
      .then(setConversations)
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex h-full flex-col gap-6">
      <Reveal>
        <PageHeader
          title="Ask AI"
          description="Ask questions across all of your documents. Answers are grounded in extracted content with citations."
          icon={<Sparkles className="size-5" />}
        />
      </Reveal>

      <Reveal delay={60} className="min-h-0 flex-1">
        <Card className="h-[calc(100vh-10rem)] min-h-[480px]">
          <CardContent className="flex h-full flex-col p-4">
            {loading ? (
              <div className="space-y-3">
                <Skeleton className="h-8 w-1/3" />
                <Skeleton className="h-full flex-1" />
                <Skeleton className="h-12" />
              </div>
            ) : (
              <ChatPanel
                conversations={conversations}
                onConversationCreated={(c) => setConversations((prev) => [c, ...prev])}
              />
            )}
          </CardContent>
        </Card>
      </Reveal>
    </div>
  );
}