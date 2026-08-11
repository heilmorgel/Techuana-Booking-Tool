<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <strong>Zeltplatz Verwaltung</strong>
        <span>Admin · Stammdaten &amp; Einstellungen</span>
      </div>
      <nav class="nav">
        <RouterLink to="/">Zeltplätze</RouterLink>
        <RouterLink to="/services">Dienste</RouterLink>
        <RouterLink to="/person-fees">Preisprofile</RouterLink>
        <RouterLink to="/operator">Betreiber</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>
