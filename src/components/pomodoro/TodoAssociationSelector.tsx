import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { CheckSquare, X } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useInsightsStore } from '@/lib/stores/insights'

interface TodoAssociationSelectorProps {
  selectedTodoId: string | null
  onTodoSelect: (todoId: string | null) => void
}

export function TodoAssociationSelector({ selectedTodoId, onTodoSelect }: TodoAssociationSelectorProps) {
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

  return (
    <div className="space-y-2">
      <Label htmlFor="todo-selector" className="flex items-center gap-2 text-base font-semibold">
        <CheckSquare className="text-primary h-5 w-5" />
        {t('pomodoro.todoAssociation.linkTodo')}
        <Badge variant="outline" className="ml-auto text-xs">
          {t('pomodoro.todoAssociation.optional')}
        </Badge>
      </Label>

      {loadingTodos ? (
        <p className="text-muted-foreground text-sm">{t('insights.loading')}</p>
      ) : pendingTodos.length === 0 ? (
        <p className="text-muted-foreground text-sm">{t('pomodoro.todoAssociation.noTodos')}</p>
      ) : (
        <div className="flex items-center gap-2">
          <Select
            value={selectedTodoId || 'none'}
            onValueChange={(value) => onTodoSelect(value === 'none' ? null : value)}>
            <SelectTrigger id="todo-selector" className="flex-1">
              <SelectValue placeholder={t('pomodoro.todoAssociation.selectTodo')}>
                {selectedTodo ? (
                  <span className="truncate">{selectedTodo.title}</span>
                ) : (
                  t('pomodoro.todoAssociation.selectTodo')
                )}
              </SelectValue>
            </SelectTrigger>
            <SelectContent
              position="item-aligned"
              className="w-[min(600px,90vw)]"
              style={{ width: 'min(600px, 90vw)', maxWidth: 'min(600px, 90vw)' }}>
              <SelectItem value="none">{t('pomodoro.todoAssociation.noTodoSelected')}</SelectItem>
              {pendingTodos.map((todo) => (
                <SelectItem
                  key={todo.id}
                  value={todo.id}
                  style={{ maxWidth: '100%', width: '100%', display: 'block', overflow: 'hidden' }}>
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.125rem',
                      width: '100%',
                      maxWidth: '100%'
                    }}>
                    <div
                      style={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        width: '100%',
                        maxWidth: '100%'
                      }}
                      className="text-sm font-medium">
                      {todo.title}
                    </div>
                    {todo.description && (
                      <div
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          width: '100%',
                          maxWidth: '100%'
                        }}
                        className="text-muted-foreground text-xs">
                        {todo.description}
                      </div>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {selectedTodoId && (
            <Button variant="ghost" size="icon" onClick={() => onTodoSelect(null)} className="h-10 w-10 shrink-0">
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      )}

      {selectedTodo && (
        <div className="border-primary/20 bg-primary/10 rounded-lg border-2 p-4">
          <div className="flex items-start gap-3">
            <CheckSquare className="text-primary mt-0.5 h-5 w-5 shrink-0" />
            <div className="flex-1 space-y-2 overflow-hidden">
              <p className="text-foreground font-semibold">{selectedTodo.title}</p>
              {selectedTodo.description && (
                <p className="text-muted-foreground line-clamp-3 text-sm">{selectedTodo.description}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
