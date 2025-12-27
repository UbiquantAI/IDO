import { useEffect } from 'react'

import { Button } from '@/components/ui/button'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

interface PresetButtonsProps {
  layout?: 'horizontal' | 'vertical'
}

/**
 * Preset buttons for quick Pomodoro configuration
 * Displays 3 preset options with auto-detection of matching config
 */
export function PresetButtons({ layout = 'horizontal' }: PresetButtonsProps) {
  const { config, presets, selectedPresetId, applyPreset, setSelectedPresetId, setPresets } = usePomodoroStore()

  // Initialize default presets if empty
  useEffect(() => {
    if (presets.length === 0) {
      setPresets([
        {
          id: 'classic',
          name: '25 - 5',
          description: 'Classic Pomodoro',
          workDurationMinutes: 25,
          breakDurationMinutes: 5,
          totalRounds: 2,
          icon: '🍅'
        },
        {
          id: 'extended',
          name: '50 - 10',
          description: 'Extended Focus',
          workDurationMinutes: 50,
          breakDurationMinutes: 10,
          totalRounds: 2,
          icon: '⏰'
        },
        {
          id: 'deep',
          name: '90 - 20',
          description: 'Deep Work',
          workDurationMinutes: 90,
          breakDurationMinutes: 20,
          totalRounds: 2,
          icon: '🚀'
        }
      ])
    }
  }, [presets.length, setPresets])

  // Auto-detect if current config matches a preset
  useEffect(() => {
    if (!selectedPresetId) {
      const matchingPreset = presets.find(
        (p) =>
          p.workDurationMinutes === config.workDurationMinutes &&
          p.breakDurationMinutes === config.breakDurationMinutes &&
          p.totalRounds === config.totalRounds
      )
      if (matchingPreset) {
        setSelectedPresetId(matchingPreset.id)
      }
    }
  }, [config, presets, selectedPresetId, setSelectedPresetId])

  const handlePresetClick = (presetId: string) => {
    setSelectedPresetId(presetId)
    applyPreset(presetId)
  }

  if (presets.length === 0) {
    return null
  }

  return (
    <div className={cn('gap-3', layout === 'vertical' ? 'flex flex-col' : 'grid grid-cols-1 sm:grid-cols-3')}>
      {presets.map((preset) => {
        const isSelected = selectedPresetId === preset.id

        return (
          <Button
            key={preset.id}
            variant={isSelected ? 'default' : 'outline'}
            className={cn(
              'h-auto flex-col gap-1 py-2',
              'transition-all duration-200',
              'hover:scale-105 hover:shadow-md',
              'active:scale-95',
              isSelected && 'ring-primary/20 ring-2'
            )}
            onClick={() => handlePresetClick(preset.id)}>
            <span className="text-xl">{preset.icon}</span>
            <span className="text-xs font-semibold">{preset.name}</span>
            <span className="text-muted-foreground text-xs">
              {preset.totalRounds} × ({preset.workDurationMinutes}m + {preset.breakDurationMinutes}
              m)
            </span>
          </Button>
        )
      })}
    </div>
  )
}
