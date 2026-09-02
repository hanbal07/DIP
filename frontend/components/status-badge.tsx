import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";

const STATUS_META: Record<
  string,
  { variant: BadgeProps["variant"]; label: string; showDot: boolean }
> = {
  pending: { variant: "warning", label: "Queued", showDot: true },
  uploaded: { variant: "info", label: "Uploaded", showDot: true },
  processing: { variant: "info", label: "Processing", showDot: true },
  completed: { variant: "success", label: "Completed", showDot: true },
  failed: { variant: "destructive", label: "Failed", showDot: true },
  needs_review: { variant: "warning", label: "Needs review", showDot: true },
  deleted: { variant: "neutral", label: "Deleted", showDot: false },
};

export function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? {
    variant: "neutral" as BadgeProps["variant"],
    label: status,
    showDot: false,
  };
  if (status === "processing" || status === "pending") {
    return (
      <Badge variant={meta.variant}>
        <Spinner className="size-3" />
        {meta.label}
      </Badge>
    );
  }
  return (
    <Badge variant={meta.variant} dot={meta.showDot}>
      {meta.label}
    </Badge>
  );
}

const REVIEW_META: Record<string, { variant: BadgeProps["variant"]; label: string }> = {
  pending: { variant: "warning", label: "Awaiting review" },
  reviewed: { variant: "success", label: "Reviewed" },
  not_required: { variant: "neutral", label: "Auto-verified" },
};

export function ReviewBadge({ reviewStatus }: { reviewStatus: string }) {
  const meta = REVIEW_META[reviewStatus] ?? {
    variant: "neutral" as BadgeProps["variant"],
    label: reviewStatus,
  };
  return (
    <Badge variant={meta.variant} dot>
      {meta.label}
    </Badge>
  );
}

export function DocumentTypeLabel({ type }: { type: string }) {
  return DOCUMENT_TYPE_LABELS[type] ?? type;
}

// Map backend document_type codes to human labels.
export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  invoice: "Invoice",
  receipt: "Receipt",
  resume: "Resume / CV",
  contract: "Contract",
  report: "Report",
  research_paper: "Research paper",
  form: "Form",
  certificate: "Certificate",
  unknown: "General document",
};

export const DOCUMENT_TYPE_DESCRIPTIONS: Record<string, string> = {
  invoice: "Payment requests with amounts, dates, and vendor details",
  receipt: "Proof-of-purchase records",
  resume: "Candidate profiles and career histories",
  contract: "Legally binding agreements and terms",
  report: "Periodic business or technical summaries",
  research_paper: "Academic and technical publications",
  form: "Structured data-entry templates",
  certificate: "Awards, licenses, and credentials",
  unknown: "Documents not matching a known schema",
};