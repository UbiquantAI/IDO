import { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface PageLayoutProps {
  children: ReactNode
  className?: string
  /** If true, applies max-width and center alignment to content. Default: true */
  centered?: boolean
  /** Maximum width for centered layout. Default: '5xl' (1024px) */
  maxWidth?: 'xl' | '2xl' | '3xl' | '4xl' | '5xl' | '6xl' | '7xl'
  /** If true, makes the page header sticky at the top. Default: false */
  stickyHeader?: boolean
}

/**
 * Page layout container
 * Provides a unified layout structure with optional centered content
 */
export function PageLayout({
  children,
  className,
  centered = true,
  maxWidth = '4xl',
  stickyHeader = false
}: PageLayoutProps) {
  const maxWidthClass = {
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
    '6xl': 'max-w-6xl',
    '7xl': 'max-w-7xl'
  }[maxWidth]

  if (!centered) {
    return <div className={cn('flex h-full flex-col', className)}>{children}</div>
  }

  if (stickyHeader) {
    // Extract header and content from children
    const childrenArray = Array.isArray(children) ? children : [children]
    const headerIndex = childrenArray.findIndex(
      (child: any) => child?.type?.name === 'PageHeader' || child?.type?.displayName === 'PageHeader'
    )

    const header = headerIndex >= 0 ? childrenArray[headerIndex] : null
    const content = childrenArray.filter((_, index) => index !== headerIndex)

    return (
      <div className={cn('flex h-full flex-col', className)}>
        {/* Sticky Header */}
        {header && (
          <div className="bg-background/95 supports-backdrop-filter:bg-background/60 sticky top-0 z-10 backdrop-blur">
            <div className={cn('mx-auto w-full', maxWidthClass)}>{header}</div>
          </div>
        )}

        {/* Content - let children handle their own scrolling */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className={cn('mx-auto flex h-full w-full flex-col', maxWidthClass)}>{content}</div>
        </div>
      </div>
    )
  }

  return (
    <div className={cn('flex h-full flex-col', className)}>
      <div className={cn('mx-auto w-full', maxWidthClass)}>{children}</div>
    </div>
  )
}
