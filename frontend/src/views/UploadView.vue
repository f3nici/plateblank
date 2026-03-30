<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'

const router = useRouter()
const isDragging = ref(false)
const files = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)

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
  uploadProgress.value = 0

  const formData = new FormData()
  for (const file of files.value) {
    formData.append('files', file)
  }

  try {
    await api.post('/images/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress(e) {
        if (e.total) {
          uploadProgress.value = Math.round((e.loaded / e.total) * 100)
        }
      },
    })
    files.value = []
    uploadProgress.value = 0
    router.push('/annotate')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-white mb-6">Upload Photos</h1>

    <div
      class="border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200 cursor-pointer"
      :class="isDragging
        ? 'border-accent bg-accent/10 shadow-lg shadow-accent/10'
        : 'border-white/10 hover:border-accent/40 hover:bg-white/[0.02]'"
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
      <div class="text-slate-400">
        <svg class="mx-auto h-12 w-12 mb-4 text-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
        </svg>
        <p class="text-lg font-medium text-slate-300">Drop images here or click to browse</p>
        <p class="text-sm mt-1 text-slate-500">JPG, PNG, WebP up to 20 MB each</p>
      </div>
    </div>

    <div v-if="files.length" class="mt-6 space-y-2">
      <div
        v-for="(file, i) in files"
        :key="i"
        class="flex items-center justify-between glass-card px-4 py-3"
      >
        <div class="flex items-center gap-3 min-w-0">
          <span class="text-sm font-medium text-slate-300 truncate">{{ file.name }}</span>
          <span class="text-xs text-slate-500">{{ formatSize(file.size) }}</span>
        </div>
        <button
          @click="removeFile(i)"
          class="text-slate-500 hover:text-red-400 text-lg transition-colors"
          :disabled="uploading"
        >&times;</button>
      </div>
    </div>

    <div v-if="uploading && uploadProgress > 0" class="mt-4">
      <div class="w-full bg-surface-400 rounded-full h-1.5 overflow-hidden">
        <div
          class="bg-gradient-to-r from-accent-dark to-accent-light h-full rounded-full transition-all duration-300"
          :style="{ width: uploadProgress + '%' }"
        ></div>
      </div>
      <p class="text-sm text-slate-500 mt-1.5 text-center">{{ uploadProgress }}%</p>
    </div>

    <button
      v-if="files.length"
      @click="upload"
      :disabled="uploading"
      class="mt-6 w-full btn-primary py-3 text-base"
    >
      {{ uploading ? 'Uploading...' : `Upload ${files.length} file${files.length > 1 ? 's' : ''}` }}
    </button>
  </div>
</template>
