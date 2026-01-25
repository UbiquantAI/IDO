import { cn } from '@/lib/utils'

function Skeleton({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div data-slot="skeleton" className={cn('bg-accent relative overflow-hidden rounded-md', className)} {...props}>
      <div className="skeleton-shimmer absolute inset-0" />
    </div>
  )
}

export { Skeleton }
