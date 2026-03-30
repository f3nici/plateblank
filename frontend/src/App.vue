<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const toast = ref(null)
let toastTimeout = null

function onApiError(event) {
  toast.value = event.detail.message
  clearTimeout(toastTimeout)
  toastTimeout = setTimeout(() => {
    toast.value = null
  }, 4000)
}

onMounted(() => {
  window.addEventListener('api-error', onApiError)
})

onUnmounted(() => {
  window.removeEventListener('api-error', onApiError)
})
</script>

<template>
  <div class="min-h-screen bg-surface-600 text-slate-200">
    <nav class="sticky top-0 z-40 bg-surface-500/80 backdrop-blur-xl border-b border-white/5">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-14 items-center">
          <router-link to="/" class="text-lg font-bold tracking-tight">
            <span class="text-accent-light">Plate</span><span class="text-white">Blank</span>
          </router-link>
          <div class="flex gap-1">
            <router-link
              v-for="link in [
                { to: '/', label: 'Upload' },
                { to: '/annotate', label: 'Annotate' },
                { to: '/results', label: 'Results' },
              ]"
              :key="link.to"
              :to="link.to"
              class="px-3.5 py-1.5 text-sm font-medium text-slate-400 rounded-lg transition-all duration-150 hover:text-white hover:bg-white/5"
              active-class="!text-accent-light !bg-accent/10"
            >
              {{ link.label }}
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>

    <!-- Toast notification -->
    <Transition name="fade">
      <div
        v-if="toast"
        class="fixed bottom-4 right-4 bg-red-500/90 backdrop-blur-sm text-white px-4 py-3 rounded-xl shadow-2xl max-w-sm z-50 border border-red-400/20"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm">{{ toast }}</span>
          <button @click="toast = null" class="text-white/70 hover:text-white ml-2">
            &times;
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
