/**
 * Skeleton Loading Component
 * Shows placeholder while data is loading
 */

export function SkeletonLoader() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-8 bg-slate-200 rounded-lg w-1/4"></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white border border-slate-200 rounded-xl p-6 h-40">
            <div className="h-4 bg-slate-200 rounded w-1/2 mb-4"></div>
            <div className="h-8 bg-slate-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
      <div className="bg-white border border-slate-200 rounded-xl p-6 h-96">
        <div className="h-4 bg-slate-200 rounded w-1/4 mb-6"></div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-slate-200 rounded"></div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Table row skeleton
 */
export function TableSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="h-10 bg-slate-200 rounded"></div>
      ))}
    </div>
  );
}

/**
 * Single card skeleton
 */
export function CardSkeleton() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 animate-pulse">
      <div className="h-4 bg-slate-200 rounded w-1/2 mb-4"></div>
      <div className="h-8 bg-slate-200 rounded w-3/4 mb-4"></div>
      <div className="h-3 bg-slate-200 rounded w-1/3"></div>
    </div>
  );
}

/**
 * Stats grid skeleton
 */
export function StatsGridSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="bg-white border border-slate-200 rounded-xl p-6">
          <div className="h-4 bg-slate-200 rounded w-1/2 mb-4"></div>
          <div className="h-8 bg-slate-200 rounded w-3/4 mb-4"></div>
          <div className="h-3 bg-slate-200 rounded w-1/3"></div>
        </div>
      ))}
    </div>
  );
}
