<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api.js'
import ThumbnailGrid from '../components/ThumbnailGrid.vue'
import ImageCanvas from '../components/ImageCanvas.vue'

const route = useRoute()
const router = useRouter()
const images = ref([])
const selectedImageId = ref(null)
const selectedImage = ref(null)
const loading = ref(true)
const processing = ref(false)

async function loadImages() {
  loading.value = true
  try {
    const res = await api.get('/images', { params: { per_page: 200 } })
    images.value = res.data.images
  } finally {
    loading.value = false
  }
}

async function selectImage(id) {
  selectedImageId.value = id
  router.replace(`/annotate/${id}`)
  const res = await api.get(`/images/${id}`)
  selectedImage.value = res.data
}

async function onPlateSaved() {
  if (selectedImageId.value) {
    const res = await api.get(`/images/${selectedImageId.value}`)
    selectedImage.value = res.data
  }
  // Refresh list in background without blocking
  api.get('/images', { params: { per_page: 200 } }).then((res) => {
    images.value = res.data.images
  })
}

async function processAll() {
  processing.value = true
  try {
    await api.post('/images/process-all')
    router.push('/results')
  } finally {
    processing.value = false
  }
}

async function processOne() {
  if (!selectedImageId.value) return
  processing.value = true
  try {
    await api.post(`/images/${selectedImageId.value}/process`)
    await loadImages()
    const res = await api.get(`/images/${selectedImageId.value}`)
    selectedImage.value = res.data
  } finally {
    processing.value = false
  }
}

function saveAndNext() {
  const currentIndex = images.value.findIndex(
    (img) => img.id === selectedImageId.value
  )
  const nextImage = images.value.find(
    (img, i) => i > currentIndex && (img.status === 'pending' || img.status === 'annotated')
  )
  if (nextImage) {
    selectImage(nextImage.id)
  }
}

async function deleteImage(id) {
  await api.delete(`/images/${id}`)
  if (selectedImageId.value === id) {
    selectedImageId.value = null
    selectedImage.value = null
  }
  await loadImages()
}

const annotatedCount = computed(
  () => images.value.filter((i) => i.status === 'annotated').length
)

onMounted(async () => {
  await loadImages()
  if (route.params.id) {
    selectImage(Number(route.params.id))
  }
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-white">Annotate Plates</h1>
      <div class="flex gap-2">
        <button
          v-if="selectedImage && selectedImage.plates?.length"
          @click="processOne"
          :disabled="processing"
          class="btn-secondary text-sm"
        >
          Process This Image
        </button>
        <button
          v-if="annotatedCount > 0"
          @click="processAll"
          :disabled="processing"
          class="btn-primary text-sm"
        >
          {{ processing ? 'Processing...' : `Process All (${annotatedCount})` }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-12 text-slate-500">Loading images...</div>

    <div v-else-if="!images.length" class="text-center py-16">
      <p class="text-slate-500 mb-4">No images uploaded yet.</p>
      <router-link to="/" class="text-accent hover:text-accent-light font-medium transition-colors">
        Upload some images
      </router-link>
    </div>

    <div v-else class="flex gap-4" style="min-height: calc(100vh - 200px)">
      <!-- Thumbnail sidebar -->
      <div class="w-48 shrink-0 overflow-y-auto pr-1">
        <ThumbnailGrid
          :images="images"
          :selected-id="selectedImageId"
          @select="selectImage"
          @delete="deleteImage"
        />
      </div>

      <!-- Canvas area -->
      <div class="flex-1 glass-card overflow-hidden">
        <div v-if="!selectedImage" class="flex items-center justify-center h-full text-slate-500">
          Select an image to annotate
        </div>
        <ImageCanvas
          v-else
          :image="selectedImage"
          @plate-saved="onPlateSaved"
          @save-and-next="saveAndNext"
        />
      </div>
    </div>
  </div>
</template>
