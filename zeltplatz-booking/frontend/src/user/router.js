import { createRouter, createWebHashHistory } from 'vue-router'
import GanttView from '../views/GanttView.vue'
import PitchCalendarView from '../views/PitchCalendarView.vue'
import BillingView from '../views/BillingView.vue'

// Hash history avoids broken routes under HA Ingress path prefixes.
const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', name: 'gantt', component: GanttView },
    { path: '/calendar', name: 'calendar', component: PitchCalendarView },
    { path: '/billing', name: 'billing', component: BillingView },
  ],
})

export default router
