import { createRouter, createWebHistory } from 'vue-router'
import GanttView from './views/GanttView.vue'
import PitchCalendarView from './views/PitchCalendarView.vue'
import AdminPitchesView from './views/AdminPitchesView.vue'
import AdminServicesView from './views/AdminServicesView.vue'
import AdminPersonFeesView from './views/AdminPersonFeesView.vue'
import AdminOperatorSettingsView from './views/AdminOperatorSettingsView.vue'
import BillingView from './views/BillingView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'gantt', component: GanttView },
    { path: '/calendar', name: 'calendar', component: PitchCalendarView },
    { path: '/billing', name: 'billing', component: BillingView },
    { path: '/admin/pitches', name: 'admin-pitches', component: AdminPitchesView },
    { path: '/admin/services', name: 'admin-services', component: AdminServicesView },
    { path: '/admin/person-fees', name: 'admin-person-fees', component: AdminPersonFeesView },
    {
      path: '/admin/operator',
      name: 'admin-operator',
      component: AdminOperatorSettingsView,
    },
  ],
})

export default router
