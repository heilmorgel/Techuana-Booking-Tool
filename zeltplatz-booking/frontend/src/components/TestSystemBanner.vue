<template>
  <div v-if="visible" class="test-system-banner" role="status">
    Testsystem — Sie befinden sich in einer Testumgebung
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

const visible = ref(Boolean(import.meta.env.DEV))

onMounted(async () => {
  if (visible.value) return
  try {
    const health = await api.health()
    if (health?.dev_mode) visible.value = true
  } catch {
    // API unreachable: no banner outside Vite DEV
  }
})
</script>
