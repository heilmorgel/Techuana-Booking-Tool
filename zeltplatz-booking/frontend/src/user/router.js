import { createRouter, createWebHistory } from 'vue-router'
import GanttView from '../views/GanttView.vue'
import PitchCalendarView from '../views/PitchCalendarView.vue'
import BillingView from '../views/BillingView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'gantt', component: GanttView },
    { path: '/calendar', name: 'calendar', component: PitchCalendarView },
    { path: '/billing', name: 'billing', component: BillingView },
  ],
})

export default router
