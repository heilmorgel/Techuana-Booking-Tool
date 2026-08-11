<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <strong>Zeltplatz Buchung</strong>
        <span>Lagerleitung · Pfadfinder-Zeltlagerplatz</span>
      </div>
      <nav class="nav">
        <RouterLink to="/">Gantt</RouterLink>
        <RouterLink to="/calendar">Kalender</RouterLink>
        <RouterLink to="/billing">Abrechnung</RouterLink>
        <RouterLink to="/admin/pitches">Zeltplätze</RouterLink>
        <RouterLink to="/admin/services">Dienste</RouterLink>
        <RouterLink to="/admin/person-fees">Personenpreise</RouterLink>
        <RouterLink to="/admin/operator">Betreiber</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>
