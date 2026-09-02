import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface SkeletonCardGridProps {
  count?: number;
  className?: string;
  columns?: string;
}

/** Consistent loading placeholder for document card grids. */
export function SkeletonCardGrid({
  count = 3,
  className,
  columns,
}: SkeletonCardGridProps) {
  return (
    <div
      className={cn(
        "grid gap-4 sm:grid-cols-2 lg:grid-cols-3",
        columns,
        className
      )}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-xl border border-border bg-card p-5 shadow-sm"
        >
          <div className="mb-4 flex items-center justify-between">
            <Skeleton className="size-10 rounded-lg" />
            <Skeleton className="size-8 rounded-md" />
          </div>
          <Skeleton className="mb-2 h-4 w-3/4" />
          <Skeleton className="mb-4 h-3 w-1/2" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}