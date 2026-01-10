import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useTranslation } from 'react-i18next'

export type TimePeriod = 'week' | 'month' | 'year'

interface TimePeriodSelectorProps {
  value: TimePeriod
  onChange: (period: TimePeriod) => void
}

export function TimePeriodSelector({ value, onChange }: TimePeriodSelectorProps) {
  const { t } = useTranslation()

  return (
    <Tabs value={value} onValueChange={(v) => onChange(v as TimePeriod)} className="w-auto">
      <TabsList>
        <TabsTrigger value="week">{t('pomodoro.review.period.week')}</TabsTrigger>
        <TabsTrigger value="month">{t('pomodoro.review.period.month')}</TabsTrigger>
        <TabsTrigger value="year">{t('pomodoro.review.period.year')}</TabsTrigger>
      </TabsList>
    </Tabs>
  )
}
