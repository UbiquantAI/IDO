import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { InsightTodo } from '@/lib/services/insights'

interface TodoCardsViewProps {
  todos: InsightTodo[]
  selectedCategory: string | null
  onComplete: (todo: InsightTodo) => void
  onDelete: (todoId: string) => void
  onExecuteInChat: (todoId: string) => void
  onTodoClick?: (todo: InsightTodo) => void
}

type TodoStatus = 'unscheduled' | 'scheduled' | 'completed' | 'all'

export function TodoCardsView({ todos, selectedCategory, onComplete, onDelete, onTodoClick }: TodoCardsViewProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<TodoStatus>('scheduled')

  // Filter todos by category first
  const categoryFilteredTodos = useMemo(() => {
    if (!selectedCategory) return todos
    return todos.filter((todo) => todo.keywords && todo.keywords.length > 0 && todo.keywords[0] === selectedCategory)
  }, [todos, selectedCategory])

  // Statistics
  const unscheduledCount = categoryFilteredTodos.filter((todo) => !todo.completed && !todo.scheduledDate).length
  const scheduledCount = categoryFilteredTodos.filter((todo) => !todo.completed && todo.scheduledDate).length
  const completedCount = categoryFilteredTodos.filter((todo) => todo.completed).length

  // Filter todos based on active tab
  const filteredTodos = categoryFilteredTodos.filter((todo) => {
    if (activeTab === 'unscheduled') return !todo.completed && !todo.scheduledDate
    if (activeTab === 'scheduled') return !todo.completed && todo.scheduledDate
    if (activeTab === 'completed') return todo.completed
    return true
  })

  return (
    <div className="flex h-full flex-col gap-6">
      {/* Statistics Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-card rounded-lg border p-4">
          <div className="text-muted-foreground mb-1 text-sm">{t('insights.todoUnscheduled', 'To Schedule')}</div>
          <div className="text-3xl font-semibold">{unscheduledCount}</div>
        </div>

        <div className="bg-card rounded-lg border p-4">
          <div className="text-muted-foreground mb-1 text-sm">{t('insights.completed', 'Completed')}</div>
          <div className="text-3xl font-semibold">{completedCount}</div>
        </div>

        <div className="bg-card rounded-lg border p-4">
          <div className="text-muted-foreground mb-1 text-sm">{t('insights.totalTodos', 'Total')}</div>
          <div className="text-3xl font-semibold">{todos.length}</div>
        </div>
      </div>

      {/* Add Todo Input */}
      {/*<div className="bg-muted/50 relative rounded-lg p-4">
        <Input
          placeholder={t('insights.addNewTodo', 'Add new task...')}
          value={newTodoTitle}
          onChange={(e) => setNewTodoTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleAddTodo()
            }
          }}
          className="bg-background pr-12"
        />
        <button
          onClick={handleAddTodo}
          className="bg-foreground text-background absolute top-1/2 right-6 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full transition-opacity hover:opacity-80">
          <Plus className="h-5 w-5" />
        </button>
      </div>*/}

      {/* Tabs */}
      <div className="bg-muted flex rounded-lg p-1">
        <button
          onClick={() => setActiveTab('unscheduled')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'unscheduled' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}>
          {t('insights.todoUnscheduled', 'To Schedule')} ({unscheduledCount})
        </button>
        <button
          onClick={() => setActiveTab('scheduled')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'scheduled' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}>
          {t('insights.todoScheduled', 'In Progress')} ({scheduledCount})
        </button>
        <button
          onClick={() => setActiveTab('completed')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'completed' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}>
          {t('insights.completed', 'Completed')} ({completedCount})
        </button>
        <button
          onClick={() => setActiveTab('all')}
          className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'all' ? 'bg-background shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}>
          {t('insights.todoStatusAll', 'All')} ({todos.length})
        </button>
      </div>

      {/* Todo List */}
      <div className="flex-1 space-y-3 overflow-y-auto">
        {filteredTodos.length === 0 ? (
          <div className="text-muted-foreground py-12 text-center">
            {activeTab === 'unscheduled' && t('insights.noUnscheduledTodos', 'No unscheduled todos')}
            {activeTab === 'scheduled' && t('insights.noScheduledTodos', 'No scheduled todos')}
            {activeTab === 'completed' && t('insights.noCompletedTodos', 'No completed todos')}
            {activeTab === 'all' && t('insights.noTodos', 'No todos')}
          </div>
        ) : (
          filteredTodos.map((todo) => (
            <div
              key={todo.id}
              className="bg-card cursor-pointer rounded-lg border p-4 transition-shadow hover:shadow-md"
              onClick={() => onTodoClick?.(todo)}>
              <div className="mb-3 flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    checked={!!todo.completed}
                    onChange={(e) => {
                      e.stopPropagation()
                      !todo.completed && onComplete(todo)
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="bg-background border-input mt-1 h-5 w-5 cursor-pointer rounded border"
                  />
                  <div>
                    <h3 className={`font-medium ${todo.completed ? 'text-muted-foreground line-through' : ''}`}>
                      {todo.title}
                    </h3>
                    {todo.description && <p className="text-muted-foreground mt-1 text-sm">{todo.description}</p>}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onDelete(todo.id)
                  }}
                  className="text-muted-foreground hover:text-destructive transition-colors">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round">
                    <path d="M3 6h18" />
                    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
                    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                  </svg>
                </button>
              </div>
              <div className="flex items-center gap-2">
                {todo.keywords && todo.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {todo.keywords.slice(0, 3).map((keyword, idx) => (
                      <span key={idx} className="bg-primary/10 text-primary rounded px-2 py-0.5 text-xs">
                        {keyword}
                      </span>
                    ))}
                  </div>
                )}
                {todo.scheduledDate && (
                  <span className="text-muted-foreground text-xs">
                    📅 {new Date(todo.scheduledDate).toLocaleDateString()}
                    {todo.scheduledTime && ` ${todo.scheduledTime}`}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
