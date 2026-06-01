import { useTranslation } from 'react-i18next'

import { ScrollArea } from '@/components/ui/scroll-area'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { usePomodoroPanelStore } from '@/lib/stores/pomodoroPanel'
import { useUIStore } from '@/lib/stores/ui'

import { PomodoroTimer } from '../PomodoroTimer'

export function FloatingPomodoroPanel() {
  const { t } = useTranslation()
  const { pomodoroFloatingPanelOpen, setPomodoroFloatingPanelOpen } = useUIStore()
  const { userIntent, selectedTodoId, setUserIntent, setSelectedTodoId, clearTask } = usePomodoroPanelStore()

  return (
    <Sheet open={pomodoroFloatingPanelOpen} onOpenChange={setPomodoroFloatingPanelOpen}>
      <SheetContent side="right" className="w-full overflow-hidden sm:w-[560px] sm:max-w-[560px]">
        <SheetHeader>
          <SheetTitle>{t('pomodoro.title')}</SheetTitle>
          <SheetDescription>{t('pomodoro.description')}</SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-120px)] px-4">
          <div className="space-y-4">
            <PomodoroTimer
              userIntent={userIntent}
              selectedTodoId={selectedTodoId}
              onUserIntentChange={setUserIntent}
              onTodoSelect={setSelectedTodoId}
              onClearTask={clearTask}
            />
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
