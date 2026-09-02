"use client";

import Link from "next/link";
import {
  File,
  FileText,
  Receipt,
  User,
  ScrollText,
  BarChart3,
  GraduationCap,
  ClipboardList,
  Award,
  MoreHorizontal,
  Eye,
  PenLine,
  Trash2,
} from "lucide-react";
import type { DocumentListItem } from "@/lib/types";
import { formatBytes, formatDate } from "@/lib/api";
import {
  StatusBadge,
  ReviewBadge,
  DocumentTypeLabel,
} from "@/components/status-badge";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const TYPE_ICONS: Record<string, React.ReactNode> = {
  invoice: <Receipt className="size-4" />,
  receipt: <Receipt className="size-4" />,
  resume: <User className="size-4" />,
  contract: <ScrollText className="size-4" />,
  report: <BarChart3 className="size-4" />,
  research_paper: <GraduationCap className="size-4" />,
  form: <ClipboardList className="size-4" />,
  certificate: <Award className="size-4" />,
};

interface DocumentCardProps {
  doc: DocumentListItem;
  onDelete?: (doc: DocumentListItem) => void;
  index?: number;
}

export function DocumentCard({ doc, onDelete, index = 0 }: DocumentCardProps) {
  const processing = doc.status === "processing" || doc.status === "pending";
  const needsReview = doc.review_status === "pending";

  return (
    <Card
      hoverable
      className="group/card flex h-full flex-col overflow-hidden"
      style={{ animationDelay: `${Math.min(index, 12) * 45}ms` }}
    >
      <CardContent className="flex flex-1 flex-col p-5">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-border/70 bg-muted/50 text-muted-foreground transition-colors duration-200 group-hover/card:border-primary/25 group-hover/card:text-primary">
            {TYPE_ICONS[doc.document_type] ?? <File className="size-4" />}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger
              asChild
              aria-label={`Actions for ${doc.filename}`}
            >
              <Button
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground opacity-0 transition-opacity duration-150 group-hover/card:opacity-100 focus-visible:opacity-100"
              >
                <MoreHorizontal className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuLabel>{doc.filename}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href={`/documents/${doc.id}`}>
                  <Eye />
                  View document
                </Link>
              </DropdownMenuItem>
              {needsReview && (
                <DropdownMenuItem asChild>
                  <Link href={`/documents/${doc.id}?tab=extraction`}>
                    <PenLine />
                    Review extraction
                  </Link>
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:bg-red-50 focus:text-destructive dark:focus:bg-red-950"
                onSelect={() => onDelete?.(doc)}
              >
                <Trash2 />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Link href={`/documents/${doc.id}`} className="block min-w-0">
          <h3 className="truncate text-sm font-semibold text-foreground transition-colors hover:text-primary">
            {doc.filename}
          </h3>
        </Link>
        <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
          <FileText className="mr-1 inline size-3 text-muted-foreground/70" />
          {doc.content_type.split("/")[1]?.toUpperCase() || "FILE"} ·{" "}
          {formatBytes(doc.file_size)} · {doc.page_count} page
          {doc.page_count === 1 ? "" : "s"}
        </p>

        {needsReview && (
          <div className="mt-3">
            <Badge variant="warning" dot>
              AI confidence low — review recommended
            </Badge>
          </div>
        )}
      </CardContent>

      <CardFooter className="mt-auto flex items-center justify-between gap-2 border-t bg-muted/30 px-5 py-3">
        <div className="flex items-center gap-2">
          <StatusBadge status={doc.status} />
          <Badge variant="neutral">
            {DocumentTypeLabel({ type: doc.document_type })}
          </Badge>
        </div>
        <ReviewBadge reviewStatus={doc.review_status} />
      </CardFooter>

      <p className="px-5 pb-3 text-[11px] leading-none text-muted-foreground/80">
        {processing ? "Processing in background…" : `Created ${formatDate(doc.created_at)}`}
      </p>
    </Card>
  );
}