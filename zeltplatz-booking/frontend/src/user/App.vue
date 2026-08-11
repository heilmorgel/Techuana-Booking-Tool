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
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>
