import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useTranslation } from 'react-i18next'
import { useSettingsStore } from '@/lib/stores/settings'
import { useTheme } from '@/components/system/theme/theme-provider'
import { languages } from '@/locales'

export function AppearanceSettings() {
  const { t, i18n } = useTranslation()
  const { theme, setTheme, fontSize, setFontSize } = useTheme()
  const updateLanguage = useSettingsStore((state) => state.updateLanguage)

  const handleLanguageChange = (value: string) => {
    i18n.changeLanguage(value)
    updateLanguage(value as 'zh-CN' | 'en-US')
  }

  const handleThemeChange = (value: string) => {
    setTheme(value as 'light' | 'dark' | 'system')
  }

  const handleFontSizeChange = (value: string) => {
    setFontSize(value as 'small' | 'default' | 'large' | 'extra-large')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('settings.appearance')}</CardTitle>
        <CardDescription>{t('settings.appearanceDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Theme settings */}
        <div className="space-y-2">
          <Label htmlFor="theme">{t('settings.theme')}</Label>
          <Select value={theme} onValueChange={handleThemeChange}>
            <SelectTrigger id="theme">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="light">{t('theme.light')}</SelectItem>
              <SelectItem value="dark">{t('theme.dark')}</SelectItem>
              <SelectItem value="system">{t('theme.system')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Language settings */}
        <div className="space-y-2">
          <Label htmlFor="language">{t('settings.language')}</Label>
          <Select value={i18n.language} onValueChange={handleLanguageChange}>
            <SelectTrigger id="language">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {languages.map((lang) => (
                <SelectItem key={lang.code} value={lang.code}>
                  {lang.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Font size settings */}
        <div className="space-y-2">
          <Label htmlFor="font-size">{t('settings.fontSize')}</Label>
          <Select value={fontSize} onValueChange={handleFontSizeChange}>
            <SelectTrigger id="font-size">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="small">{t('settings.fontSizeSmall')}</SelectItem>
              <SelectItem value="default">{t('settings.fontSizeDefault')}</SelectItem>
              <SelectItem value="large">{t('settings.fontSizeLarge')}</SelectItem>
              <SelectItem value="extra-large">{t('settings.fontSizeExtraLarge')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  )
}
