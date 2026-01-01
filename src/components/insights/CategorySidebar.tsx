import { useTranslation } from 'react-i18next'
import { Folder } from 'lucide-react'
import { InsightKnowledge } from '@/lib/services/insights'

interface CategorySidebarProps {
  knowledge: InsightKnowledge[]
  selectedCategory: string | null
  onCategoryChange: (category: string | null) => void
}

export function CategorySidebar({ knowledge, selectedCategory, onCategoryChange }: CategorySidebarProps) {
  const { t } = useTranslation()

  // Extract categories from keywords (use first keyword as category)
  const categoryCounts = knowledge.reduce(
    (acc, item) => {
      if (item.keywords && item.keywords.length > 0) {
        const category = item.keywords[0]
        acc[category] = (acc[category] || 0) + 1
      }
      return acc
    },
    {} as Record<string, number>
  )

  const categories = Object.entries(categoryCounts)
    .sort(([, a], [, b]) => b - a) // Sort by count descending
    .map(([category, count]) => ({ category, count }))

  const totalCount = knowledge.length

  return (
    <div className="flex w-64 flex-shrink-0 flex-col overflow-hidden">
      <div className="mb-4 flex-shrink-0">
        <h3 className="text-muted-foreground mb-3 text-sm font-medium">{t('insights.categories')}</h3>

        {/* All categories */}
        <button
          onClick={() => onCategoryChange(null)}
          className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
            selectedCategory === null
              ? 'bg-muted text-foreground'
              : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
          }`}>
          <div className="flex items-center gap-2">
            <Folder className="h-4 w-4" />
            <span>{t('insights.allCategories')}</span>
          </div>
          <span className="text-muted-foreground text-xs">{totalCount}</span>
        </button>
      </div>

      {/* Category list - scrollable */}
      <div className="flex-1 space-y-1 overflow-y-auto pr-2">
        {categories.map(({ category, count }) => (
          <button
            key={category}
            onClick={() => onCategoryChange(category)}
            className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors ${
              selectedCategory === category
                ? 'bg-muted text-foreground'
                : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
            }`}>
            <div className="flex min-w-0 items-center gap-2">
              <Folder className="h-4 w-4 flex-shrink-0" />
              <span className="truncate">{category}</span>
            </div>
            <span className="text-muted-foreground ml-2 flex-shrink-0 text-xs">{count}</span>
          </button>
        ))}
      </div>

      {categories.length === 0 && (
        <div className="text-muted-foreground flex-1 py-8 text-center text-xs">{t('insights.noKnowledge')}</div>
      )}
    </div>
  )
}
