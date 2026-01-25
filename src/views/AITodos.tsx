import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { useInsightsStore } from '@/lib/stores/insights'
import { PendingTodoList } from '@/components/insights/PendingTodoList'
import { TodoCalendarView } from '@/components/insights/TodoCalendarView'
import { TodoCardsView } from '@/components/insights/TodoCardsView'
import { TodosDetailDialog } from '@/components/insights/TodosDetailDialog'
import { ViewModeToggle } from '@/components/insights/ViewModeToggle'
import { LoadingPage } from '@/components/shared/LoadingPage'
import { Bot, ListTodo, Plus, X } from 'lucide-react'
import { EmptyState } from '@/components/shared/EmptyState'
import { ScrollToTop } from '@/components/shared/ScrollToTop'
import { emitTodoToChat } from '@/lib/events/eventBus'
import { PageHeader } from '@/components/layout/PageHeader'
import { PageLayout } from '@/components/layout/PageLayout'
import { Button } from '@/components/ui/button'
import type { InsightTodo, RecurrenceRule } from '@/lib/services/insights'
import {
  registerTodoDropHandler,
  unregisterTodoDropHandler,
  type DraggedTodoData,
  type TodoDragTarget
} from '@/lib/drag/todoDragController'
import { useTodoSync } from '@/hooks/useTodoSync'
import { CreateTodoDialog } from '@/components/insights/CreateTodoDialog'
import { TodoCategorySidebar } from '@/components/insights/TodoCategorySidebar'

type ViewMode = 'calendar' | 'cards'

export default function AITodosView() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()

  // View mode state
  const [viewMode, setViewMode] = useState<ViewMode>('cards')

  // Enable TODO auto-sync
  useTodoSync()

  // Insights store
  const todos = useInsightsStore((state) => state.todos)
  const loading = useInsightsStore((state) => state.loadingTodos)
  const refreshTodos = useInsightsStore((state) => state.refreshTodos)
  const removeTodo = useInsightsStore((state) => state.removeTodo)
  const completeTodo = useInsightsStore((state) => state.completeTodo)
  const unscheduleTodo = useInsightsStore((state) => state.unscheduleTodo)
  const scheduleTodo = useInsightsStore((state) => state.scheduleTodo)
  const getPendingTodos = useInsightsStore((state) => state.getPendingTodos)
  const getScheduledTodos = useInsightsStore((state) => state.getScheduledTodos)
  const getTodosByDate = useInsightsStore((state) => state.getTodosByDate)

  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedTodoId, setSelectedTodoId] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Get fresh todos for dialog from store (not a snapshot)
  const dialogTodos = selectedDate
    ? getTodosByDate(selectedDate)
    : selectedTodoId
      ? todos.filter((t) => t.id === selectedTodoId)
      : []

  useEffect(() => {
    void refreshTodos(true) // Load all todos including completed ones
  }, [refreshTodos])

  const pendingTodos = getPendingTodos()
  const scheduledTodos = getScheduledTodos()

  // Handle date cell click - opens dialog with todos for that date
  const handleDateClick = useCallback(
    (date: string) => {
      const todosForDate = getTodosByDate(date)
      if (todosForDate.length > 0) {
        setSelectedDate(date)
        setDialogOpen(true)
      }
    },
    [getTodosByDate]
  )

  // Handle completing a todo
  const handleCompleteTodo = useCallback(
    async (todo: InsightTodo) => {
      try {
        await completeTodo(todo.id)
        toast.success(t('insights.todoCompleted', 'Todo completed'))
        // Check if dialog should close (no more todos for this date or single todo)
        if (selectedDate) {
          const remainingTodos = getTodosByDate(selectedDate).filter((t) => t.id !== todo.id)
          if (remainingTodos.length === 0) {
            setDialogOpen(false)
          }
        } else if (selectedTodoId === todo.id) {
          // If this was a single todo dialog, close it
          setDialogOpen(false)
        }
      } catch (error) {
        console.error('Failed to complete todo:', error)
        toast.error(t('insights.completeFailed', 'Failed to complete todo'))
      }
    },
    [completeTodo, getTodosByDate, selectedDate, selectedTodoId, t]
  )

  // Handle unscheduling a todo
  const handleUnscheduleTodo = useCallback(
    async (todo: InsightTodo) => {
      try {
        await unscheduleTodo(todo.id)
        toast.success(t('insights.todoUnscheduledMessage', 'Todo unscheduled'))
        setDialogOpen(false)
      } catch (error) {
        console.error('Failed to unschedule todo:', error)
        toast.error(t('insights.unscheduleFailed', 'Failed to unschedule todo'))
      }
    },
    [unscheduleTodo, t]
  )

  // Handle updating todo schedule (time range and recurrence)
  const handleUpdateSchedule = useCallback(
    async (
      todo: InsightTodo,
      scheduledDate: string,
      scheduledTime?: string,
      scheduledEndTime?: string,
      recurrenceRule?: RecurrenceRule
    ) => {
      console.log('[AITodos] handleUpdateSchedule called:', {
        todoId: todo.id,
        title: todo.title,
        scheduledDate,
        scheduledTime,
        scheduledEndTime,
        endTimeType: typeof scheduledEndTime,
        recurrenceRule
      })
      try {
        await scheduleTodo(todo.id, scheduledDate, scheduledTime, scheduledEndTime, recurrenceRule)
        toast.success(t('insights.scheduleUpdated', 'Schedule updated'))
        // dialogTodos will automatically update from store
      } catch (error) {
        console.error('Failed to update schedule:', error)
        toast.error(t('insights.scheduleUpdateFailed', 'Failed to update schedule'))
      }
    },
    [scheduleTodo, t]
  )

  // Handle executing a todo in Chat (agent execution)
  const handleExecuteInChat = async (todoOrId: InsightTodo | string) => {
    const todoId = typeof todoOrId === 'string' ? todoOrId : todoOrId.id
    const todo = todos.find((t) => t.id === todoId)
    if (!todo) return

    try {
      toast.success(t('insights.redirectingToChat'))
      navigate('/chat')

      // Publish the event after a 200ms delay
      setTimeout(() => {
        emitTodoToChat({
          todoId: todo.id,
          title: todo.title,
          description: todo.description,
          keywords: todo.keywords,
          createdAt: todo.createdAt
        })
      }, 200)
    } catch (error) {
      console.error('Failed to execute todo in chat:', error)
      toast.error(t('insights.executeInChatFailed'))
    }
  }

  // Handle deleting a todo
  const handleDeleteTodo = async (todoId: string) => {
    try {
      await removeTodo(todoId)
      toast.success(t('insights.todoDeleted', 'Todo deleted'))
    } catch (error) {
      console.error('Failed to delete todo:', error)
      toast.error(t('insights.deleteFailed', 'Failed to delete todo'))
    }
  }

  // Handle clicking a todo card to open details
  const handleTodoClick = useCallback((todo: InsightTodo) => {
    if (todo.scheduledDate) {
      // For scheduled todos, show all todos on that date
      setSelectedDate(todo.scheduledDate)
      setSelectedTodoId(null)
    } else {
      // For unscheduled todos, show only this todo
      setSelectedDate(null)
      setSelectedTodoId(todo.id)
    }
    setDialogOpen(true)
  }, [])

  // Handle dragging todos onto the calendar
  const formatScheduledLabel = useCallback(
    (date: string, time?: string) => {
      try {
        const locale = i18n.language?.startsWith('zh') ? 'zh-CN' : 'en-US'
        const iso = time ? `${date}T${time}` : `${date}T00:00`
        const formatter = new Intl.DateTimeFormat(locale, {
          month: 'short',
          day: 'numeric',
          ...(time
            ? {
                hour: '2-digit',
                minute: '2-digit'
              }
            : {})
        })
        return formatter.format(new Date(iso))
      } catch {
        return time ? `${date} ${time}` : date
      }
    },
    [i18n.language]
  )

  // Helper function to calculate end time (1 hour after start time)
  const calculateEndTime = useCallback((startTime: string): string => {
    const [hours, minutes] = startTime.split(':').map(Number)
    const endHour = (hours + 1) % 24
    return `${String(endHour).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
  }, [])

  const handleDropToCalendar = useCallback(
    async (todoId: string, date: string, time?: string) => {
      console.log('[AITodos] handleDropToCalendar called:', { todoId, date, time })
      try {
        setSelectedDate(date)

        // If time is provided, automatically set end time to 1 hour later
        const startTime = time || '09:00'
        const endTime = time ? calculateEndTime(time) : '10:00'

        console.log('[AITodos] Scheduling with default duration:', { startTime, endTime })
        await scheduleTodo(todoId, date, startTime, endTime)

        const label = formatScheduledLabel(date, time)
        toast.success(`${t('insights.todoScheduled', 'Todo scheduled')} · ${label}`)
      } catch (error) {
        console.error('Failed to schedule todo:', error)
        toast.error(t('insights.scheduleFailed', 'Failed to schedule todo'))
      }
    },
    [formatScheduledLabel, scheduleTodo, t, setSelectedDate, calculateEndTime]
  )

  // Use ref to store latest handler to avoid re-registration
  const dropHandlerRef = useRef<((todo: DraggedTodoData, target: TodoDragTarget) => void) | undefined>(undefined)

  // Update ref when dependencies change
  useEffect(() => {
    dropHandlerRef.current = (todo: DraggedTodoData, target: TodoDragTarget) => {
      console.log('[AITodos] dropHandlerRef.current called:', todo, target)
      void handleDropToCalendar(todo.id, target.date, target.time)
    }
  }, [handleDropToCalendar])

  // Register stable wrapper only once
  useEffect(() => {
    const stableHandler = (todo: DraggedTodoData, target: TodoDragTarget) => {
      console.log('[AITodos] stableHandler called:', todo, target)
      dropHandlerRef.current?.(todo, target)
    }
    console.log('[AITodos] Registering drop handler')
    registerTodoDropHandler(stableHandler)
    return () => {
      console.log('[AITodos] Unregistering drop handler')
      unregisterTodoDropHandler(stableHandler)
    }
  }, [])

  if (loading && todos.length === 0) {
    return <LoadingPage message={t('insights.loading', 'Loading...')} />
  }

  return (
    <PageLayout stickyHeader maxWidth="5xl">
      <PageHeader
        title={t('insights.pendingTodos', 'Pending Todos')}
        description={t('insights.todosGeneratedFromActivities')}
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-1 h-4 w-4" />
              {t('insights.createTodo', 'Create Todo')}
            </Button>
            <ViewModeToggle viewMode={viewMode} onViewModeChange={setViewMode} />
          </div>
        }
      />

      {viewMode === 'cards' ? (
        <div className="animate-in fade-in slide-in-from-bottom-2 flex h-full flex-1 gap-6 overflow-hidden px-6 pb-6 duration-300">
          {/* Left Sidebar - Categories */}
          <TodoCategorySidebar
            todos={todos}
            selectedCategory={selectedCategory}
            onCategoryChange={setSelectedCategory}
          />

          {/* Main Content */}
          <div className="flex flex-1 flex-col overflow-hidden">
            <TodoCardsView
              todos={todos}
              selectedCategory={selectedCategory}
              onComplete={handleCompleteTodo}
              onDelete={handleDeleteTodo}
              onExecuteInChat={handleExecuteInChat}
              onTodoClick={handleTodoClick}
            />
          </div>
        </div>
      ) : (
        <div className="animate-in fade-in slide-in-from-bottom-2 flex h-full flex-1 gap-6 overflow-hidden px-6 pb-6 duration-300">
          {/* Left column: calendar */}
          <div className="flex flex-1 flex-col overflow-hidden">
            <TodoCalendarView todos={scheduledTodos} selectedDate={selectedDate} onDateSelect={handleDateClick} />
          </div>

          {/* Right column: pending section - hidden on small screens */}
          <div className="hidden w-80 shrink-0 flex-col overflow-hidden rounded-lg border xl:flex">
            <div className="shrink-0 border-b px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold">{t('insights.pendingTodos', 'Pending todos')}</h2>
                  <p className="text-muted-foreground text-xs">
                    {pendingTodos.length} {t('insights.todosCount', 'todos')}
                  </p>
                </div>
              </div>
            </div>

            <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
              {pendingTodos.length === 0 ? (
                <EmptyState
                  icon={Bot}
                  title={t('insights.noPendingTodos', 'No pending todos')}
                  description={t(
                    'insights.todosGeneratedFromActivities',
                    'AI will automatically generate todos from your activities'
                  )}
                />
              ) : (
                <PendingTodoList
                  todos={pendingTodos}
                  onExecuteInChat={handleExecuteInChat}
                  onDelete={handleDeleteTodo}
                  onComplete={handleCompleteTodo}
                  onSchedule={handleUpdateSchedule}
                />
              )}
            </div>
            <ScrollToTop containerRef={scrollContainerRef} />
          </div>

          {/* Floating button to open sidebar on small screens */}
          <Button
            className="bg-primary text-primary-foreground fixed right-6 bottom-6 h-14 w-14 rounded-full shadow-lg xl:hidden"
            size="icon"
            onClick={() => setSidebarOpen(true)}>
            <ListTodo className="h-6 w-6" />
          </Button>

          {/* Overlay sidebar for small screens */}
          {sidebarOpen && (
            <>
              {/* Backdrop */}
              <div className="fixed inset-0 z-40 bg-black/50 xl:hidden" onClick={() => setSidebarOpen(false)} />

              {/* Sidebar */}
              <div className="bg-background fixed top-0 right-0 bottom-0 z-50 flex w-80 flex-col shadow-xl xl:hidden">
                <div className="flex shrink-0 items-center justify-between border-b px-4 py-3">
                  <div>
                    <h2 className="font-semibold">{t('insights.pendingTodos', 'Pending todos')}</h2>
                    <p className="text-muted-foreground text-xs">
                      {pendingTodos.length} {t('insights.todosCount', 'todos')}
                    </p>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                <div className="flex-1 overflow-y-auto">
                  {pendingTodos.length === 0 ? (
                    <EmptyState
                      icon={Bot}
                      title={t('insights.noPendingTodos', 'No pending todos')}
                      description={t(
                        'insights.todosGeneratedFromActivities',
                        'AI will automatically generate todos from your activities'
                      )}
                    />
                  ) : (
                    <PendingTodoList
                      todos={pendingTodos}
                      onExecuteInChat={handleExecuteInChat}
                      onDelete={handleDeleteTodo}
                      onComplete={handleCompleteTodo}
                      onSchedule={handleUpdateSchedule}
                    />
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Todos Detail Dialog - shared between both views */}
      <TodosDetailDialog
        todos={dialogTodos}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onComplete={handleCompleteTodo}
        onDelete={(todo) => handleDeleteTodo(todo.id)}
        onUnschedule={handleUnscheduleTodo}
        onUpdateSchedule={handleUpdateSchedule}
        onSendToChat={handleExecuteInChat}
      />

      {/* Create Todo Dialog */}
      <CreateTodoDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSuccess={() => refreshTodos(true)}
      />
    </PageLayout>
  )
}
