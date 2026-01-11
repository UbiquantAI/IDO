import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ListTodo, X, Target } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useInsightsStore } from '@/lib/stores/insights'

interface TodoAssociationSelectorProps {
  selectedTodoId: string | null
  onTodoSelect: (todoId: string | null) => void
  userIntent?: string
  onUserIntentChange?: (value: string) => void
  disabled?: boolean
}

export function TodoAssociationSelector({
  selectedTodoId,
  onTodoSelect,
  userIntent = '',
  onUserIntentChange,
  disabled = false
}: TodoAssociationSelectorProps) {
  const { t } = useTranslation()
  const { getScheduledTodos, todos, refreshTodos, loadingTodos } = useInsightsStore()
  const [pendingTodos, setPendingTodos] = useState<typeof todos>([])

  // Load todos on mount if not already loaded
  useEffect(() => {
    if (todos.length === 0 && !loadingTodos) {
      refreshTodos(false)
    }
  }, [])

  useEffect(() => {
    setPendingTodos(getScheduledTodos())
  }, [todos, getScheduledTodos])

  const selectedTodo = pendingTodos.find((todo) => todo.id === selectedTodoId)

  // When disabled (active session), show current task
  if (disabled) {
    const hasTask = selectedTodoId || (userIntent && userIntent.trim())
    if (hasTask) {
      return (
        <div className="flex flex-col items-center gap-2.5 py-2">
          <div className="bg-primary/15 ring-primary/20 flex items-center gap-1.5 rounded-full px-3 py-1 shadow-sm ring-1">
            <Target className="text-primary h-3.5 w-3.5" />
            <span className="text-primary text-xs font-semibold tracking-wide uppercase">
              {t('pomodoro.intent.current')}
            </span>
          </div>
          <span className="text-center text-base leading-snug font-semibold">{selectedTodo?.title || userIntent}</span>
        </div>
      )
    }
  }

  return (
    <div className="space-y-3">
      {/* When todo is selected, show todo details instead of manual input */}
      {selectedTodo ? (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ListTodo className="text-primary h-4 w-4" />
              <span className="text-xs font-medium">{t('pomodoro.todoAssociation.linkedTodo')}</span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onTodoSelect(null)}
              disabled={disabled}
              className="text-muted-foreground hover:text-foreground -mr-2 h-8 gap-1.5 px-3 text-xs transition-all">
              <X className="h-3.5 w-3.5" />
              {t('pomodoro.taskSelector.clearTask')}
            </Button>
          </div>
          <div className="bg-muted/30 border-border/40 rounded-lg border p-3">
            <p className="text-sm leading-snug font-semibold">{selectedTodo.title}</p>
            {selectedTodo.description && (
              <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{selectedTodo.description}</p>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* TODO selector */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-xs font-medium">
              <ListTodo className="text-muted-foreground h-3.5 w-3.5" />
              {t('pomodoro.todoAssociation.linkTodo')}
            </label>

            {loadingTodos ? (
              <div className="bg-muted/20 flex h-9 items-center justify-center rounded-lg border">
                <p className="text-muted-foreground text-xs">{t('insights.loading')}</p>
              </div>
            ) : pendingTodos.length === 0 ? (
              <div className="bg-muted/20 flex h-9 items-center justify-center rounded-lg border">
                <p className="text-muted-foreground text-xs">{t('pomodoro.todoAssociation.noTodos')}</p>
              </div>
            ) : (
              <Select
                value="none"
                onValueChange={(value) => onTodoSelect(value === 'none' ? null : value)}
                disabled={disabled}>
                <SelectTrigger className="h-9 !text-xs">
                  <SelectValue placeholder={t('pomodoro.todoAssociation.selectTodo')} />
                </SelectTrigger>
                <SelectContent position="popper" className="max-h-[280px] w-(--radix-select-trigger-width)">
                  <SelectItem value="none">{t('pomodoro.todoAssociation.noTodoSelected')}</SelectItem>
                  {pendingTodos.map((todo) => (
                    <SelectItem key={todo.id} value={todo.id}>
                      <div className="flex flex-col gap-0.5">
                        <span className="text-xs font-medium">{todo.title}</span>
                        {todo.description && (
                          <span className="text-muted-foreground line-clamp-1 text-[10px]">{todo.description}</span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Manual input for task description */}
          <div className="space-y-2">
            <label className="flex items-center gap-2 text-xs font-medium">
              <Target className="text-muted-foreground h-3.5 w-3.5" />
              {t('pomodoro.intent.label')}
            </label>
            <Input
              placeholder={t('pomodoro.intent.placeholder')}
              value={userIntent}
              onChange={(e) => onUserIntentChange?.(e.target.value)}
              maxLength={200}
              disabled={disabled}
              className="h-9 !text-xs placeholder:!text-xs"
            />
          </div>
        </div>
      )}
    </div>
  )
}
