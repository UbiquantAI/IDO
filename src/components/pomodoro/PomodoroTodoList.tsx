import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ListTodo, CheckCircle2, Tag } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useInsightsStore } from '@/lib/stores/insights'
import { cn } from '@/lib/utils'
import type { InsightTodo } from '@/lib/services/insights'
import { PomodoroStats } from './PomodoroStats'

interface PomodoroTodoListProps {
  selectedTodoId: string | null
  onTodoSelect: (todo: InsightTodo) => void
  disabled?: boolean
}

/**
 * Pomodoro sidebar component showing pending todos for quick selection
 * Displays todos in a compact, scannable list with visual feedback
 */
export function PomodoroTodoList({ selectedTodoId, onTodoSelect, disabled = false }: PomodoroTodoListProps) {
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

  return (
    <Card className="border-border/40 ring-border/5 flex h-[700px] flex-col py-6 ring-1 backdrop-blur-sm">
      {/* Pomodoro Statistics - Horizontal Layout */}

      <div className="border-border/40 border-b px-4 pb-6">
        <PomodoroStats />
      </div>

      <CardHeader className="border-border/40 shrink-0 py-0!">
        <CardTitle className="flex items-center gap-2.5 pb-0 text-base">
          <div className="bg-primary/15 ring-primary/20 rounded-lg p-2 ring-1">
            <ListTodo className="text-primary h-4 w-4" />
          </div>
          <span className="flex-1">{t('insights.todoScheduled', 'In Progress')}</span>
          <Badge variant="secondary" className="bg-muted/60 text-foreground/80 px-2.5 py-0.5 text-sm font-semibold">
            {pendingTodos.length}
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="overflow-hidden p-0">
        {loadingTodos ? (
          <div className="flex items-center justify-center p-6">
            <div className="text-center">
              <div className="bg-muted/40 mx-auto mb-3 h-12 w-12 animate-pulse rounded-full" />
              <p className="text-muted-foreground text-sm font-medium">{t('insights.loading')}</p>
            </div>
          </div>
        ) : pendingTodos.length === 0 ? (
          <div className="flex items-center justify-center p-6">
            <div className="text-center">
              <div className="bg-muted/30 mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl">
                <CheckCircle2 className="text-muted-foreground/50 h-8 w-8" />
              </div>
              <p className="text-muted-foreground text-sm font-medium">
                {t('insights.noScheduledTodos', 'No scheduled tasks')}
              </p>
              <p className="text-muted-foreground/60 mt-1 text-xs">
                {t('pomodoro.todoList.scheduleHint', 'Schedule todos in calendar to start')}
              </p>
            </div>
          </div>
        ) : (
          <ScrollArea className="h-[700px]">
            <div className="space-y-2 p-4">
              {pendingTodos.map((todo) => {
                const isSelected = selectedTodoId === todo.id
                return (
                  <button
                    key={todo.id}
                    onClick={() => !disabled && onTodoSelect(todo)}
                    disabled={disabled}
                    className={cn(
                      'group relative w-full overflow-hidden rounded-xl border p-3.5 text-left transition-all duration-200',
                      'hover:shadow-md active:scale-[0.98]',
                      isSelected
                        ? 'border-primary/40 bg-primary/10 ring-primary/20 shadow-sm ring-1'
                        : 'border-border/50 bg-card hover:border-border hover:bg-muted/30',
                      disabled && 'cursor-not-allowed opacity-60'
                    )}>
                    {/* Selection indicator */}
                    {isSelected && (
                      <div className="bg-primary animate-in fade-in slide-in-from-left-2 absolute top-0 left-0 h-full w-1 duration-300" />
                    )}

                    <div className="flex flex-col gap-2">
                      {/* Title */}
                      <h4
                        className={cn(
                          'truncate text-sm leading-snug font-semibold transition-colors',
                          isSelected ? 'text-primary' : 'text-foreground group-hover:text-foreground'
                        )}>
                        {todo.title}
                      </h4>

                      {/* Description */}
                      {todo.description && (
                        <p className="text-muted-foreground line-clamp-2 text-xs leading-relaxed">{todo.description}</p>
                      )}

                      {/* Keywords */}
                      {todo.keywords && todo.keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {todo.keywords.slice(0, 3).map((keyword, idx) => (
                            <div
                              key={idx}
                              className={cn(
                                'flex max-w-[140px] items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-medium transition-colors',
                                isSelected
                                  ? 'bg-primary/20 text-primary'
                                  : 'bg-muted/60 text-muted-foreground group-hover:bg-muted'
                              )}>
                              <Tag className="h-2.5 w-2.5 shrink-0" />
                              <span className="truncate">{keyword}</span>
                            </div>
                          ))}
                          {todo.keywords.length > 3 && (
                            <span className="text-muted-foreground/60 text-[10px]">+{todo.keywords.length - 3}</span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Hover effect overlay */}
                    <div
                      className={cn(
                        'pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-200',
                        'from-primary/5 bg-linear-to-br to-transparent',
                        !disabled && 'group-hover:opacity-100'
                      )}
                    />
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
