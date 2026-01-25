import { useTranslation } from 'react-i18next'
import { Calendar, LayoutGrid } from 'lucide-react'

type ViewMode = 'calendar' | 'cards'

interface ViewModeToggleProps {
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
}

export function ViewModeToggle({ viewMode, onViewModeChange }: ViewModeToggleProps) {
  const { t } = useTranslation()

  return (
    <div className="bg-muted flex rounded-lg p-1">
      <button
        onClick={() => onViewModeChange('calendar')}
        className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          viewMode === 'calendar' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
        }`}>
        <Calendar className="h-4 w-4" />
        {t('insights.viewModeCalendar', 'Calendar')}
      </button>
      <button
        onClick={() => onViewModeChange('cards')}
        className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
          viewMode === 'cards' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
        }`}>
        <LayoutGrid className="h-4 w-4" />
        {t('insights.viewModeCards', 'Cards')}
      </button>
    </div>
  )
}
