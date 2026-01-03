import { create } from 'zustand'
import {
  deleteDiary,
  deleteKnowledge,
  deleteTodo,
  fetchDiaryList,
  fetchKnowledgeList,
  fetchRecentEvents,
  fetchTodoList,
  generateDiary,
  InsightDiary,
  InsightEvent,
  InsightKnowledge,
  InsightTodo,
  toggleKnowledgeFavorite,
  createKnowledge,
  updateKnowledge,
  type RecurrenceRule
} from '@/lib/services/insights'

interface InsightsState {
  recentEvents: InsightEvent[]
  knowledge: InsightKnowledge[]
  todos: InsightTodo[]
  diaries: InsightDiary[]

  recentEventsLimit: number
  todoIncludeCompleted: boolean

  loadingEvents: boolean
  loadingKnowledge: boolean
  loadingTodos: boolean
  loadingDiaries: boolean
  lastError?: string

  fetchRecentEvents: (limit?: number) => Promise<void>
  refreshKnowledge: () => Promise<void>
  refreshTodos: (includeCompleted?: boolean) => Promise<void>
  refreshDiaries: (limit?: number) => Promise<void>

  removeKnowledge: (id: string) => Promise<void>
  removeTodo: (id: string) => Promise<void>
  removeDiary: (id: string) => Promise<void>

  // Knowledge favorites
  toggleKnowledgeFavorite: (id: string) => Promise<void>
  createKnowledge: (title: string, description: string, keywords: string[]) => Promise<InsightKnowledge>
  updateKnowledge: (id: string, title: string, description: string, keywords: string[]) => Promise<void>

  // Todo scheduling
  scheduleTodo: (
    id: string,
    date: string,
    time?: string,
    endTime?: string,
    recurrenceRule?: RecurrenceRule
  ) => Promise<void>
  unscheduleTodo: (id: string) => Promise<void>
  completeTodo: (id: string) => Promise<void>
  getTodosByDate: (date: string) => InsightTodo[]
  getPendingTodos: () => InsightTodo[]
  getScheduledTodos: () => InsightTodo[]

  createDiaryForDate: (date: string) => Promise<InsightDiary>
  clearError: () => void
  setRecentEventsLimit: (limit: number) => void
}

const DEFAULT_EVENT_LIMIT = 5

export const useInsightsStore = create<InsightsState>((set, get) => ({
  recentEvents: [],
  knowledge: [],
  todos: [],
  diaries: [],

  recentEventsLimit: DEFAULT_EVENT_LIMIT,
  todoIncludeCompleted: false,

  loadingEvents: false,
  loadingKnowledge: false,
  loadingTodos: false,
  loadingDiaries: false,
  lastError: undefined,

  fetchRecentEvents: async (limit) => {
    const finalLimit = limit ?? get().recentEventsLimit
    set({ loadingEvents: true, recentEventsLimit: finalLimit, lastError: undefined })
    try {
      const events = await fetchRecentEvents(finalLimit)
      set({ recentEvents: events })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingEvents: false })
    }
  },

  refreshKnowledge: async () => {
    set({ loadingKnowledge: true, lastError: undefined })
    try {
      const knowledge = await fetchKnowledgeList()
      set({ knowledge })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingKnowledge: false })
    }
  },

  refreshTodos: async (includeCompleted) => {
    const finalInclude = includeCompleted ?? get().todoIncludeCompleted
    set({ loadingTodos: true, todoIncludeCompleted: finalInclude, lastError: undefined })
    try {
      const todos = await fetchTodoList(finalInclude)
      set({ todos })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingTodos: false })
    }
  },

  refreshDiaries: async (limit = 10) => {
    set({ loadingDiaries: true, lastError: undefined })
    try {
      const diaries = await fetchDiaryList(limit)
      set({ diaries })
    } catch (error) {
      set({ lastError: error instanceof Error ? error.message : String(error) })
    } finally {
      set({ loadingDiaries: false })
    }
  },

  removeKnowledge: async (id: string) => {
    await deleteKnowledge(id)
    set((state) => ({ knowledge: state.knowledge.filter((item) => item.id !== id) }))
  },

  removeTodo: async (id: string) => {
    await deleteTodo(id)
    set((state) => ({ todos: state.todos.filter((item) => item.id !== id) }))
  },

  removeDiary: async (id: string) => {
    await deleteDiary(id)
    set((state) => ({ diaries: state.diaries.filter((item) => item.id !== id) }))
  },

  toggleKnowledgeFavorite: async (id: string) => {
    try {
      const updatedKnowledge = await toggleKnowledgeFavorite(id)
      set((state) => ({
        knowledge: state.knowledge.map((item) => (item.id === id ? updatedKnowledge : item))
      }))
    } catch (error) {
      console.error('Failed to toggle knowledge favorite:', error)
      throw error
    }
  },

  createKnowledge: async (title: string, description: string, keywords: string[]) => {
    try {
      const newKnowledge = await createKnowledge(title, description, keywords)
      set((state) => ({ knowledge: [newKnowledge, ...state.knowledge] }))
      return newKnowledge
    } catch (error) {
      console.error('Failed to create knowledge:', error)
      throw error
    }
  },

  updateKnowledge: async (id: string, title: string, description: string, keywords: string[]) => {
    try {
      const updatedKnowledge = await updateKnowledge(id, title, description, keywords)
      set((state) => ({
        knowledge: state.knowledge.map((item) => (item.id === id ? updatedKnowledge : item))
      }))
    } catch (error) {
      console.error('Failed to update knowledge:', error)
      throw error
    }
  },

  // Todo scheduling methods
  scheduleTodo: async (id: string, date: string, time?: string, endTime?: string, recurrenceRule?: RecurrenceRule) => {
    console.log('[Store] scheduleTodo called:', {
      id,
      date,
      time,
      endTime,
      endTimeType: typeof endTime,
      recurrenceRule
    })
    try {
      const { scheduleTodo: scheduleAPI } = await import('@/lib/services/insights')
      const updatedTodo = await scheduleAPI(id, date, time, endTime, recurrenceRule)
      console.log('[Store] scheduleTodo API returned:', {
        id: updatedTodo.id,
        scheduledTime: updatedTodo.scheduledTime,
        scheduledEndTime: updatedTodo.scheduledEndTime,
        endTimeType: typeof updatedTodo.scheduledEndTime
      })
      set((state) => ({
        todos: state.todos.map((todo) => (todo.id === id ? updatedTodo : todo))
      }))
    } catch (error) {
      console.error('Failed to schedule todo:', error)
      throw error
    }
  },

  completeTodo: async (id: string) => {
    try {
      const { completeTodo: completeAPI } = await import('@/lib/services/insights')
      // Call API to mark as completed
      await completeAPI(id)
      // Update local state to mark as completed
      set((state) => ({
        todos: state.todos.map((todo) => (todo.id === id ? { ...todo, completed: true } : todo))
      }))
    } catch (error) {
      console.error('Failed to complete todo:', error)
      throw error
    }
  },

  unscheduleTodo: async (id: string) => {
    try {
      const { unscheduleTodo: unscheduleAPI } = await import('@/lib/services/insights')
      const updatedTodo = await unscheduleAPI(id)
      set((state) => ({
        todos: state.todos.map((todo) => (todo.id === id ? updatedTodo : todo))
      }))
    } catch (error) {
      console.error('Failed to unschedule todo:', error)
      throw error
    }
  },

  getTodosByDate: (date: string) => {
    return get().todos.filter((todo) => todo.scheduledDate === date && !todo.completed)
  },

  getPendingTodos: () => {
    return get().todos.filter((todo) => !todo.scheduledDate && !todo.completed)
  },

  getScheduledTodos: () => {
    return get().todos.filter((todo) => todo.scheduledDate && !todo.completed)
  },

  createDiaryForDate: async (date: string) => {
    const diary = await generateDiary(date)
    set((state) => ({ diaries: [diary, ...state.diaries.filter((item) => item.id !== diary.id)] }))
    return diary
  },

  clearError: () => set({ lastError: undefined }),

  setRecentEventsLimit: (limit: number) => {
    set({ recentEventsLimit: Math.max(1, limit) })
  }
}))
