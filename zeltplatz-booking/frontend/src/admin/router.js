import { createRouter, createWebHistory } from 'vue-router'
import AdminPitchesView from '../views/AdminPitchesView.vue'
import AdminServicesView from '../views/AdminServicesView.vue'
import AdminPersonFeesView from '../views/AdminPersonFeesView.vue'
import AdminOperatorSettingsView from '../views/AdminOperatorSettingsView.vue'

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes: [
    { path: '/', name: 'admin-pitches', component: AdminPitchesView },
    { path: '/services', name: 'admin-services', component: AdminServicesView },
    { path: '/person-fees', name: 'admin-person-fees', component: AdminPersonFeesView },
    { path: '/operator', name: 'admin-operator', component: AdminOperatorSettingsView },
  ],
})

export default router
