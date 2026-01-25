import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, Check, Trash2, Calendar, CircleDot } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
  const [searchQuery, setSearchQuery] = useState('')

  // Filter todos by category first
  const categoryFilteredTodos = useMemo(() => {
    let filtered = todos
    if (selectedCategory) {
      filtered = todos.filter(
        (todo) => todo.keywords && todo.keywords.length > 0 && todo.keywords[0] === selectedCategory
      )
    }
    // Then filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (todo) =>
          todo.title.toLowerCase().includes(query) ||
          (todo.description && todo.description.toLowerCase().includes(query))
      )
    }
    return filtered
  }, [todos, selectedCategory, searchQuery])

  // Filter todos based on active tab
  const filteredTodos = categoryFilteredTodos.filter((todo) => {
    if (activeTab === 'unscheduled') return !todo.completed && !todo.scheduledDate
    if (activeTab === 'scheduled') return !todo.completed && todo.scheduledDate
    if (activeTab === 'completed') return todo.completed
    return true
  })

  // Calculate counts for tabs based on category/search filtered results
  const unscheduledCount = categoryFilteredTodos.filter((todo) => !todo.completed && !todo.scheduledDate).length
  const scheduledCount = categoryFilteredTodos.filter((todo) => !todo.completed && todo.scheduledDate).length
  const completedCount = categoryFilteredTodos.filter((todo) => todo.completed).length

  return (
    <div className="flex h-full flex-col gap-6">
      {/* Search Box */}
      <div className="relative">
        <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2" />
        <Input
          type="text"
          placeholder={t('insights.searchTodos', '搜索待办事项...')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
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
            {searchQuery.trim()
              ? t('insights.noSearchResults', '没有找到匹配的待办事项')
              : activeTab === 'unscheduled'
                ? t('insights.noUnscheduledTodos', 'No unscheduled todos')
                : activeTab === 'scheduled'
                  ? t('insights.noScheduledTodos', 'No scheduled todos')
                  : activeTab === 'completed'
                    ? t('insights.noCompletedTodos', 'No completed todos')
                    : t('insights.noTodos', 'No todos')}
          </div>
        ) : (
          filteredTodos.map((todo, i) => (
            <div
              key={todo.id}
              className="group animate-in fade-in slide-in-from-bottom-2 bg-card relative cursor-pointer rounded-lg border p-4 shadow-sm transition-shadow duration-200 hover:shadow-md"
              style={{ animationDelay: `${i * 30}ms`, animationFillMode: 'backwards' }}
              onClick={() => onTodoClick?.(todo)}>
              <div className="flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  {/* Title and description */}
                  <div className="mb-3">
                    <h3
                      className={`text-sm leading-tight font-medium ${todo.completed ? 'text-muted-foreground line-through' : ''}`}>
                      {todo.title}
                    </h3>
                    {todo.description && (
                      <p className="text-muted-foreground mt-1 line-clamp-2 text-xs leading-5">{todo.description}</p>
                    )}
                  </div>

                  {/* Footer: tags and date */}
                  <div className="flex flex-wrap items-center gap-2">
                    {todo.keywords && todo.keywords.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {todo.keywords.slice(0, 3).map((keyword, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    )}
                    {todo.scheduledDate && (
                      <div className="text-muted-foreground flex items-center gap-1 text-xs">
                        <Calendar className="h-3 w-3" />
                        <span>
                          {new Date(todo.scheduledDate).toLocaleDateString()}
                          {todo.scheduledTime && ` ${todo.scheduledTime}`}
                        </span>
                      </div>
                    )}
                    {!todo.scheduledDate && !todo.completed && (
                      <div className="text-muted-foreground flex items-center gap-1 text-xs">
                        <CircleDot className="h-3 w-3" />
                        <span>{t('insights.todoUnscheduled', 'Unscheduled')}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Hover action buttons */}
                <div className="-mt-1 flex shrink-0 gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      !todo.completed && onComplete(todo)
                    }}
                    className="h-8 w-8"
                    title={t('insights.markComplete')}>
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(todo.id)
                    }}
                    className="text-muted-foreground hover:text-destructive h-8 w-8"
                    title={t('insights.delete')}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
