<script setup>
import { ref, onMounted } from 'vue'
import { getSessionToken } from '../api.js'
import api from '../api.js'

const images = ref([])
const loading = ref(true)
const showOriginal = ref({})

async function loadImages() {
  loading.value = true
  try {
    const res = await api.get('/images', {
      params: { status: 'processed', per_page: 200 },
    })
    images.value = res.data.images
  } finally {
    loading.value = false
  }
}

function toggleOriginal(id) {
  showOriginal.value[id] = !showOriginal.value[id]
}

function downloadOne(image) {
  const token = getSessionToken()
  window.open(`/api/images/${image.id}/download?session_token=${token}`, '_blank')
}

async function downloadAll() {
  const res = await api.post('/images/download-all', null, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'plateblank_redacted.zip'
  a.click()
  URL.revokeObjectURL(url)
}

function imageUrl(image, type) {
  const token = getSessionToken()
  if (type === 'original') return `/api/images/${image.id}/original?session_token=${token}`
  return `/api/images/${image.id}/download?session_token=${token}`
}

onMounted(loadImages)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">Results</h1>
      <button
        v-if="images.length"
        @click="downloadAll"
        class="btn-primary text-sm"
      >
        Download All as ZIP
      </button>
    </div>

    <div v-if="loading" class="text-center py-12 text-slate-500">Loading...</div>

    <div v-else-if="!images.length" class="text-center py-16">
      <p class="text-slate-500 mb-4">No processed images yet.</p>
      <router-link to="/annotate" class="text-accent hover:text-accent-light font-medium transition-colors">
        Go annotate some plates
      </router-link>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="image in images"
        :key="image.id"
        class="glass-card-hover overflow-hidden group"
      >
        <div class="relative aspect-video bg-surface-500 overflow-hidden">
          <img
            :src="imageUrl(image, showOriginal[image.id] ? 'original' : 'processed')"
            :alt="image.filename"
            class="w-full h-full object-contain transition-transform duration-300 group-hover:scale-105"
          />
          <span
            v-if="showOriginal[image.id]"
            class="absolute top-2 left-2 bg-yellow-500/90 text-white text-xs px-2 py-0.5 rounded-lg"
          >
            Original
          </span>
        </div>
        <div class="p-3 flex items-center justify-between border-t border-white/5">
          <span class="text-sm text-slate-400 truncate" :title="image.filename">
            {{ image.filename }}
          </span>
          <div class="flex gap-2 shrink-0">
            <button
              @click="toggleOriginal(image.id)"
              class="text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded-lg bg-surface-300 transition-colors"
            >
              {{ showOriginal[image.id] ? 'Redacted' : 'Original' }}
            </button>
            <button
              @click="downloadOne(image)"
              class="text-xs text-accent hover:text-accent-light px-2.5 py-1 rounded-lg bg-accent/10 transition-colors"
            >
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
