/**
 * Notification Sound and Clock Settings Component
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { useTranslation } from 'react-i18next'
import { useSettingsStore } from '@/lib/stores/settings'
import { audioService } from '@/lib/audio'

export function VoiceClockSettings() {
  const { t } = useTranslation()
  const { settings, updateVoiceSettings, updateClockSettings } = useSettingsStore()

  const voiceSettings = settings.voice || {
    enabled: true,
    volume: 0.8,
    soundTheme: '8bit' as const
  }

  const clockSettings = settings.clock || {
    enabled: true,
    position: 'bottom-right' as const,
    size: 'medium' as const
  }

  const handleVoiceEnabledChange = async (enabled: boolean) => {
    await updateVoiceSettings({ enabled })
  }

  const handleVoiceVolumeChange = async (value: number[]) => {
    await updateVoiceSettings({ volume: value[0] })
  }

  const handleSoundThemeChange = async (soundTheme: '8bit' | '16bit' | 'custom') => {
    await updateVoiceSettings({ soundTheme })
  }

  const handleClockEnabledChange = async (enabled: boolean) => {
    await updateClockSettings({ enabled })
  }

  const handleClockPositionChange = async (position: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left') => {
    await updateClockSettings({ position })
  }

  const handleClockSizeChange = async (size: 'small' | 'medium' | 'large') => {
    await updateClockSettings({ size })
  }

  const testSound = (soundId: 'work-complete' | 'break-complete' | 'session-complete') => {
    audioService.playSound(soundId, voiceSettings.volume).catch((error) => {
      console.error('Failed to play test sound:', error)
    })
  }

  return (
    <div className="space-y-6">
      {/* Notification Sound Settings */}
      <Card>
        <CardHeader>
          <CardTitle>{t('settings.voice.title')}</CardTitle>
          <CardDescription>{t('settings.voice.description')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Enable Notification Sounds */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>{t('settings.voice.enableTitle')}</Label>
              <p className="text-muted-foreground text-xs">{t('settings.voice.enableDescription')}</p>
            </div>
            <Switch checked={voiceSettings.enabled} onCheckedChange={handleVoiceEnabledChange} />
          </div>

          {voiceSettings.enabled && (
            <>
              {/* Volume */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>{t('settings.voice.volume')}</Label>
                  <span className="text-muted-foreground text-sm">{Math.round(voiceSettings.volume * 100)}%</span>
                </div>
                <Slider
                  value={[voiceSettings.volume]}
                  onValueChange={handleVoiceVolumeChange}
                  min={0}
                  max={1}
                  step={0.1}
                  className="w-full"
                />
              </div>

              {/* Sound Theme */}
              <div className="space-y-2">
                <Label>{t('settings.voice.soundTheme')}</Label>
                <Select value={voiceSettings.soundTheme} onValueChange={handleSoundThemeChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="8bit">{t('settings.voice.theme8bit')}</SelectItem>
                    <SelectItem value="16bit">{t('settings.voice.theme16bit')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Test Sounds */}
              <div className="space-y-2">
                <Label>{t('settings.voice.testSounds')}</Label>
                <div className="flex flex-col gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => testSound('work-complete')}
                    className="justify-start">
                    {t('settings.voice.testWorkComplete')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => testSound('break-complete')}
                    className="justify-start">
                    {t('settings.voice.testBreakComplete')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => testSound('session-complete')}
                    className="justify-start">
                    {t('settings.voice.testSessionComplete')}
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Clock Settings */}
      <Card>
        <CardHeader>
          <CardTitle>{t('settings.clock.title')}</CardTitle>
          <CardDescription>{t('settings.clock.description')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Enable Clock */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>{t('settings.clock.enableTitle')}</Label>
              <p className="text-muted-foreground text-xs">{t('settings.clock.enableDescription')}</p>
            </div>
            <Switch checked={clockSettings.enabled} onCheckedChange={handleClockEnabledChange} />
          </div>

          {clockSettings.enabled && (
            <>
              {/* Position */}
              <div className="space-y-2">
                <Label>{t('settings.clock.position')}</Label>
                <Select value={clockSettings.position} onValueChange={handleClockPositionChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bottom-right">{t('settings.voice.positions.bottom-right')}</SelectItem>
                    <SelectItem value="bottom-left">{t('settings.voice.positions.bottom-left')}</SelectItem>
                    <SelectItem value="top-right">{t('settings.voice.positions.top-right')}</SelectItem>
                    <SelectItem value="top-left">{t('settings.voice.positions.top-left')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Size */}
              <div className="space-y-2">
                <Label>{t('settings.clock.size')}</Label>
                <Select value={clockSettings.size} onValueChange={handleClockSizeChange}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="small">{t('settings.voice.sizes.small')}</SelectItem>
                    <SelectItem value="medium">{t('settings.voice.sizes.medium')}</SelectItem>
                    <SelectItem value="large">{t('settings.voice.sizes.large')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
