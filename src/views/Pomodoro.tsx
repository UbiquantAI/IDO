import { useTranslation } from 'react-i18next'
import { useState } from 'react'

import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { PomodoroTimer } from '@/components/pomodoro/PomodoroTimer'
import { PomodoroTodoList } from '@/components/pomodoro/PomodoroTodoList'
import type { InsightTodo } from '@/lib/services/insights'
import { usePomodoroStore } from '@/lib/stores/pomodoro'

export default function Pomodoro() {
  const { t } = useTranslation()
  const { status } = usePomodoroStore()
  const [userIntent, setUserIntent] = useState('')
  const [selectedTodoId, setSelectedTodoId] = useState<string | null>(null)

  const handleTodoSelect = (todo: InsightTodo) => {
    setSelectedTodoId(todo.id)
    // Don't set userIntent - let it be controlled by manual input only
  }

  return (
    <PageLayout stickyHeader>
      <PageHeader title={t('pomodoro.title')} description={t('pomodoro.description')} />

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto flex w-full max-w-[1600px] gap-6">
          {/* Left Sidebar - Todo List */}
          <aside className="hidden w-[360px] shrink-0 md:block">
            <div className="sticky top-6">
              <PomodoroTodoList
                selectedTodoId={selectedTodoId}
                onTodoSelect={handleTodoSelect}
                disabled={status === 'active'}
              />
            </div>
          </aside>

          {/* Main Content - Pomodoro Timer */}
          <main className="min-w-0 flex-1">
            <PomodoroTimer
              userIntent={userIntent}
              selectedTodoId={selectedTodoId}
              onTodoSelect={setSelectedTodoId}
              onUserIntentChange={setUserIntent}
              onClearTask={() => {
                setUserIntent('')
                setSelectedTodoId(null)
              }}
            />
          </main>
        </div>
      </div>
    </PageLayout>
  )
}
