<script setup>
import { ref, onMounted } from 'vue'
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
  window.open(`/api/images/${image.id}/download`, '_blank')
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
  if (type === 'original') return `/api/images/${image.id}/original`
  return `/api/images/${image.id}/download`
}

onMounted(loadImages)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Results</h1>
      <button
        v-if="images.length"
        @click="downloadAll"
        class="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700"
      >
        Download All as ZIP
      </button>
    </div>

    <div v-if="loading" class="text-center py-12 text-gray-500">Loading...</div>

    <div v-else-if="!images.length" class="text-center py-12">
      <p class="text-gray-500 mb-4">No processed images yet.</p>
      <router-link to="/annotate" class="text-blue-600 hover:text-blue-700 font-medium">
        Go annotate some plates
      </router-link>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="image in images"
        :key="image.id"
        class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
      >
        <div class="relative aspect-video bg-gray-100">
          <img
            :src="imageUrl(image, showOriginal[image.id] ? 'original' : 'processed')"
            :alt="image.filename"
            class="w-full h-full object-contain"
          />
          <span
            v-if="showOriginal[image.id]"
            class="absolute top-2 left-2 bg-yellow-500 text-white text-xs px-2 py-0.5 rounded"
          >
            Original
          </span>
        </div>
        <div class="p-3 flex items-center justify-between">
          <span class="text-sm text-gray-700 truncate" :title="image.filename">
            {{ image.filename }}
          </span>
          <div class="flex gap-2 shrink-0">
            <button
              @click="toggleOriginal(image.id)"
              class="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 border rounded"
            >
              {{ showOriginal[image.id] ? 'Redacted' : 'Original' }}
            </button>
            <button
              @click="downloadOne(image)"
              class="text-xs text-blue-600 hover:text-blue-700 px-2 py-1 border border-blue-200 rounded"
            >
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
