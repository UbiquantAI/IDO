import { useTranslation } from 'react-i18next'

type FilterType = 'all' | 'favorites' | 'recent'

interface KnowledgeFilterTabsProps {
  activeFilter: FilterType
  onFilterChange: (filter: FilterType) => void
}

export function KnowledgeFilterTabs({ activeFilter, onFilterChange }: KnowledgeFilterTabsProps) {
  const { t } = useTranslation()

  const tabs: { key: FilterType; label: string }[] = [
    { key: 'all', label: t('insights.allKnowledge') },
    { key: 'favorites', label: t('insights.favorites') },
    { key: 'recent', label: t('insights.recent') }
  ]

  return (
    <div className="flex gap-6 border-b">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onFilterChange(tab.key)}
          className={`relative pb-3 text-sm font-medium transition-colors ${
            activeFilter === tab.key ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
          }`}>
          {tab.label}
          {activeFilter === tab.key && <div className="bg-primary absolute right-0 bottom-0 left-0 h-0.5" />}
        </button>
      ))}
    </div>
  )
}
