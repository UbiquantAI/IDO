import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ListTodo, X } from 'lucide-react'

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
  const { getPendingTodos, todos, refreshTodos, loadingTodos } = useInsightsStore()
  const [pendingTodos, setPendingTodos] = useState<typeof todos>([])

  // Load todos on mount if not already loaded
  useEffect(() => {
    if (todos.length === 0 && !loadingTodos) {
      refreshTodos(false)
    }
  }, [])

  useEffect(() => {
    setPendingTodos(getPendingTodos())
  }, [todos, getPendingTodos])

  const selectedTodo = pendingTodos.find((todo) => todo.id === selectedTodoId)

  // When disabled (active session), show current task
  if (disabled) {
    const hasTask = selectedTodoId || (userIntent && userIntent.trim())
    if (hasTask) {
      return (
        <div className="flex flex-col items-center gap-2">
          <span className="text-muted-foreground text-sm">{t('pomodoro.intent.current')}</span>
          <span className="text-center font-medium">{selectedTodo?.title || userIntent}</span>
        </div>
      )
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {/* When todo is selected, show todo details instead of manual input */}
      {selectedTodo ? (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ListTodo className="text-primary h-4 w-4" />
              <label className="text-muted-foreground text-sm">{t('pomodoro.todoAssociation.linkedTodo')}</label>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onTodoSelect(null)}
              disabled={disabled}
              className="text-muted-foreground hover:text-foreground h-7 gap-1 px-2 text-xs">
              <X className="h-3 w-3" />
              {t('pomodoro.taskSelector.clearTask')}
            </Button>
          </div>
          <div className="bg-muted/50 rounded-md p-3">
            <p className="font-medium">{selectedTodo.title}</p>
            {selectedTodo.description && (
              <p className="text-muted-foreground mt-1 text-sm">{selectedTodo.description}</p>
            )}
          </div>
        </div>
      ) : (
        <>
          {/* TODO selector */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <ListTodo className="text-muted-foreground h-4 w-4" />
              <label className="text-muted-foreground text-sm">{t('pomodoro.todoAssociation.linkTodo')}</label>
            </div>

            {loadingTodos ? (
              <p className="text-muted-foreground text-sm">{t('insights.loading')}</p>
            ) : pendingTodos.length === 0 ? (
              <p className="text-muted-foreground text-sm">{t('pomodoro.todoAssociation.noTodos')}</p>
            ) : (
              <Select
                value="none"
                onValueChange={(value) => onTodoSelect(value === 'none' ? null : value)}
                disabled={disabled}>
                <SelectTrigger>
                  <SelectValue placeholder={t('pomodoro.todoAssociation.selectTodo')} />
                </SelectTrigger>
                <SelectContent
                  position="popper"
                  className="max-h-[300px] w-[min(400px,calc(100vw-2rem))] overflow-y-auto">
                  <SelectItem value="none">{t('pomodoro.todoAssociation.noTodoSelected')}</SelectItem>
                  {pendingTodos.map((todo) => (
                    <SelectItem key={todo.id} value={todo.id} className="max-w-full">
                      <div className="flex max-w-[350px] flex-col gap-0.5 overflow-hidden">
                        <span className="truncate text-sm font-medium">{todo.title}</span>
                        {todo.description && (
                          <span className="text-muted-foreground truncate text-xs">{todo.description}</span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          {/* Manual input for task description */}
          <div className="space-y-1.5">
            <label className="text-muted-foreground text-sm">{t('pomodoro.intent.label')}</label>
            <Input
              placeholder={t('pomodoro.intent.placeholder')}
              value={userIntent}
              onChange={(e) => onUserIntentChange?.(e.target.value)}
              maxLength={200}
              disabled={disabled}
            />
          </div>
        </>
      )}
    </div>
  )
}
