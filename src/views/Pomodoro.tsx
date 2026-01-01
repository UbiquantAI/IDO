import { useTranslation } from 'react-i18next'

import { PageLayout } from '@/components/layout/PageLayout'
import { PageHeader } from '@/components/layout/PageHeader'
import { PomodoroTimer } from '@/components/pomodoro/PomodoroTimer'

export default function Pomodoro() {
  const { t } = useTranslation()

  return (
    <PageLayout maxWidth="2xl">
      <PageHeader title={t('pomodoro.title')} description={t('pomodoro.description')} />

      <div className="flex-1 overflow-y-auto px-6 py-2">
        <PomodoroTimer />
      </div>
    </PageLayout>
  )
}
