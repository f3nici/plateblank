<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'

const router = useRouter()
const isDragging = ref(false)
const files = ref([])
const uploading = ref(false)
const uploadProgress = ref({})

function onDragOver(e) {
  e.preventDefault()
  isDragging.value = true
}

function onDragLeave() {
  isDragging.value = false
}

function onDrop(e) {
  e.preventDefault()
  isDragging.value = false
  addFiles(e.dataTransfer.files)
}

function onFileSelect(e) {
  addFiles(e.target.files)
  e.target.value = ''
}

function addFiles(fileList) {
  const allowed = ['.jpg', '.jpeg', '.png', '.webp']
  for (const file of fileList) {
    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (allowed.includes(ext)) {
      files.value.push(file)
    }
  }
}

function removeFile(index) {
  files.value.splice(index, 1)
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function upload() {
  if (!files.value.length) return
  uploading.value = true

  const formData = new FormData()
  for (const file of files.value) {
    formData.append('files', file)
  }

  try {
    await api.post('/images/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress(e) {
        if (e.total) {
          uploadProgress.value.percent = Math.round((e.loaded / e.total) * 100)
        }
      },
    })
    files.value = []
    uploadProgress.value = {}
    router.push('/annotate')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">Upload Photos</h1>

    <div
      class="border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer"
      :class="isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'"
      @dragover="onDragOver"
      @dragleave="onDragLeave"
      @drop="onDrop"
      @click="$refs.fileInput.click()"
    >
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".jpg,.jpeg,.png,.webp"
        class="hidden"
        @change="onFileSelect"
      />
      <div class="text-gray-500">
        <svg class="mx-auto h-12 w-12 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
        </svg>
        <p class="text-lg font-medium">Drop images here or click to browse</p>
        <p class="text-sm mt-1">JPG, PNG, WebP up to 20 MB each</p>
      </div>
    </div>

    <div v-if="files.length" class="mt-6 space-y-2">
      <div
        v-for="(file, i) in files"
        :key="i"
        class="flex items-center justify-between bg-white rounded-lg px-4 py-3 shadow-sm"
      >
        <div class="flex items-center gap-3 min-w-0">
          <span class="text-sm font-medium text-gray-700 truncate">{{ file.name }}</span>
          <span class="text-xs text-gray-400">{{ formatSize(file.size) }}</span>
        </div>
        <button
          @click="removeFile(i)"
          class="text-gray-400 hover:text-red-500 text-lg"
          :disabled="uploading"
        >&times;</button>
      </div>
    </div>

    <div v-if="uploading && uploadProgress.percent != null" class="mt-4">
      <div class="w-full bg-gray-200 rounded-full h-2">
        <div
          class="bg-blue-600 h-2 rounded-full transition-all"
          :style="{ width: uploadProgress.percent + '%' }"
        ></div>
      </div>
      <p class="text-sm text-gray-500 mt-1 text-center">{{ uploadProgress.percent }}%</p>
    </div>

    <button
      v-if="files.length"
      @click="upload"
      :disabled="uploading"
      class="mt-6 w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {{ uploading ? 'Uploading...' : `Upload ${files.length} file${files.length > 1 ? 's' : ''}` }}
    </button>
  </div>
</template>
