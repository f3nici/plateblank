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
  }, 5000)
}

onMounted(() => {
  window.addEventListener('api-error', onApiError)
})

onUnmounted(() => {
  window.removeEventListener('api-error', onApiError)
})
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-14 items-center">
          <router-link to="/" class="text-xl font-bold text-gray-900">
            PlateBlank
          </router-link>
          <div class="flex gap-6">
            <router-link
              to="/"
              class="text-sm font-medium text-gray-600 hover:text-gray-900"
              active-class="text-gray-900"
            >
              Upload
            </router-link>
            <router-link
              to="/annotate"
              class="text-sm font-medium text-gray-600 hover:text-gray-900"
              active-class="text-gray-900"
            >
              Annotate
            </router-link>
            <router-link
              to="/results"
              class="text-sm font-medium text-gray-600 hover:text-gray-900"
              active-class="text-gray-900"
            >
              Results
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <router-view />
    </main>

    <!-- Toast notification -->
    <Transition name="fade">
      <div
        v-if="toast"
        class="fixed bottom-4 right-4 bg-red-600 text-white px-4 py-3 rounded-lg shadow-lg max-w-sm z-50"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm">{{ toast }}</span>
          <button @click="toast = null" class="text-white/80 hover:text-white ml-2">
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
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
