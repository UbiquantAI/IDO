import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Settings, ChevronUp, ChevronDown } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { usePomodoroStore } from '@/lib/stores/pomodoro'
import { cn } from '@/lib/utils'

interface PomodoroConfigProps {
  onConfigChange?: (config: { workDurationMinutes: number; breakDurationMinutes: number; totalRounds: number }) => void
}

export function PomodoroConfig({ onConfigChange }: PomodoroConfigProps) {
  const { t } = useTranslation()
  const { config, presets, setConfig, applyPreset, setPresets } = usePomodoroStore()

  // Load presets from backend on mount
  useEffect(() => {
    async function loadPresets() {
      try {
        const response = await fetch('/api/pomodoro/presets')
        const data = await response.json()
        if (data.success && data.data) {
          setPresets(data.data)
        }
      } catch (error) {
        console.error('Failed to load Pomodoro presets:', error)
      }
    }
    loadPresets()
  }, [setPresets])

  const handlePresetSelect = (presetId: string) => {
    applyPreset(presetId)
    const preset = presets.find((p) => p.id === presetId)
    if (preset && onConfigChange) {
      onConfigChange({
        workDurationMinutes: preset.workDurationMinutes,
        breakDurationMinutes: preset.breakDurationMinutes,
        totalRounds: preset.totalRounds
      })
    }
  }

  const handleCustomChange = (field: keyof typeof config, value: number) => {
    const newConfig = { ...config, [field]: value }
    setConfig(newConfig)
    if (onConfigChange) {
      onConfigChange(newConfig)
    }
  }

  const adjustValue = (field: keyof typeof config, delta: number) => {
    const currentValue = config[field]
    let newValue = currentValue + delta

    // Set limits based on field
    if (field === 'totalRounds') {
      newValue = Math.max(1, Math.min(8, newValue))
    } else if (field === 'workDurationMinutes') {
      newValue = Math.max(5, Math.min(120, newValue))
    } else if (field === 'breakDurationMinutes') {
      newValue = Math.max(1, Math.min(60, newValue))
    }

    handleCustomChange(field, newValue)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5" />
          {t('pomodoro.config.title')}
        </CardTitle>
        <CardDescription>{t('pomodoro.config.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="presets" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="presets">{t('pomodoro.config.presets')}</TabsTrigger>
            <TabsTrigger value="custom">{t('pomodoro.config.custom')}</TabsTrigger>
          </TabsList>

          {/* Presets Tab */}
          <TabsContent value="presets" className="space-y-4">
            <div className="grid gap-3">
              {presets.map((preset) => (
                <Button
                  key={preset.id}
                  variant={
                    config.workDurationMinutes === preset.workDurationMinutes &&
                    config.breakDurationMinutes === preset.breakDurationMinutes &&
                    config.totalRounds === preset.totalRounds
                      ? 'default'
                      : 'outline'
                  }
                  className="h-auto justify-start p-4 text-left"
                  onClick={() => handlePresetSelect(preset.id)}>
                  <div className="flex w-full items-center gap-3">
                    <span className="text-2xl">{preset.icon}</span>
                    <div className="flex-1">
                      <div className="font-semibold">{preset.name}</div>
                      <div className="text-muted-foreground text-xs">{preset.description}</div>
                      <div className="mt-1 text-xs">
                        {preset.workDurationMinutes}m work / {preset.breakDurationMinutes}m break × {preset.totalRounds}{' '}
                        {t('pomodoro.config.rounds')}
                      </div>
                    </div>
                  </div>
                </Button>
              ))}
            </div>
          </TabsContent>

          {/* Custom Tab - Circular Controls */}
          <TabsContent value="custom" className="space-y-6 py-4">
            {/* Circular Adjusters */}
            <div className="flex items-center justify-center gap-8">
              {/* Total Rounds */}
              <div className="flex flex-col items-center gap-3">
                <div className="relative flex flex-col items-center">
                  {/* Up Arrow */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-foreground h-10 w-10 transition-colors"
                    onClick={() => adjustValue('totalRounds', 1)}>
                    <ChevronUp className="h-6 w-6" />
                  </Button>
                  {/* Circle with number */}
                  <div
                    className={cn(
                      'flex h-28 w-28 items-center justify-center rounded-full border-4 shadow-lg transition-all',
                      'border-border bg-card hover:border-primary hover:shadow-xl'
                    )}>
                    <span className="text-5xl font-bold tabular-nums">{config.totalRounds}</span>
                  </div>
                  {/* Down Arrow */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-foreground h-10 w-10 transition-colors"
                    onClick={() => adjustValue('totalRounds', -1)}>
                    <ChevronDown className="h-6 w-6" />
                  </Button>
                </div>
                <span className="text-muted-foreground text-sm font-medium">{t('pomodoro.config.totalRounds')}</span>
              </div>

              {/* Work Duration */}
              <div className="flex flex-col items-center gap-3">
                <div className="relative flex flex-col items-center">
                  {/* Up Arrow */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-foreground h-10 w-10 transition-colors"
                    onClick={() => adjustValue('workDurationMinutes', 5)}>
                    <ChevronUp className="h-6 w-6" />
                  </Button>
                  {/* Circle with number */}
                  <div
                    className={cn(
                      'flex h-28 w-28 items-center justify-center rounded-full border-4 shadow-lg transition-all',
                      'border-border bg-card hover:border-primary hover:shadow-xl'
                    )}>
                    <span className="text-5xl font-bold tabular-nums">{config.workDurationMinutes}</span>
                  </div>
                  {/* Down Arrow */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-foreground h-10 w-10 transition-colors"
                    onClick={() => adjustValue('workDurationMinutes', -5)}>
                    <ChevronDown className="h-6 w-6" />
                  </Button>
                </div>
                <span className="text-muted-foreground text-sm font-medium">{t('pomodoro.config.workDuration')}</span>
              </div>

              {/* Break Duration */}
              <div className="flex flex-col items-center gap-3">
                <div className="relative flex flex-col items-center">
                  {/* Up Arrow */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-foreground h-10 w-10 transition-colors"
                    onClick={() => adjustValue('breakDurationMinutes', 1)}>
                    <ChevronUp className="h-6 w-6" />
                  </Button>
                  {/* Circle with number */}
                  <div
                    className={cn(
                      'flex h-28 w-28 items-center justify-center rounded-full border-4 shadow-lg transition-all',
                      'border-border bg-card hover:border-primary hover:shadow-xl'
                    )}>
                    <span className="text-5xl font-bold tabular-nums">{config.breakDurationMinutes}</span>
                  </div>
                  {/* Down Arrow */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-muted-foreground hover:text-foreground h-10 w-10 transition-colors"
                    onClick={() => adjustValue('breakDurationMinutes', -1)}>
                    <ChevronDown className="h-6 w-6" />
                  </Button>
                </div>
                <span className="text-muted-foreground text-sm font-medium">{t('pomodoro.config.breakDuration')}</span>
              </div>
            </div>

            {/* Summary */}
            <div className="bg-muted rounded-lg p-3 text-center text-sm">
              <div className="font-medium">{t('pomodoro.config.summary')}</div>
              <div className="text-muted-foreground mt-1">
                {t('pomodoro.config.totalTime')}:{' '}
                {(config.workDurationMinutes + config.breakDurationMinutes) * config.totalRounds -
                  config.breakDurationMinutes}{' '}
                {t('pomodoro.config.minutes')}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
