<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'

const router = useRouter()
const isDragging = ref(false)
const files = ref([])
const uploading = ref(false)
const uploadProgress = ref(0)
const serverProcessing = ref(false)

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
    const promise = api.post('/images/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress(e) {
        if (e.total) {
          const pct = Math.round((e.loaded / e.total) * 100)
          uploadProgress.value = pct
          if (pct >= 100) {
            serverProcessing.value = true
          }
        }
      },
    })
    await promise
    files.value = []
    uploadProgress.value = 0
    serverProcessing.value = false
    router.push('/annotate')
  } finally {
    uploading.value = false
    serverProcessing.value = false
  }
}
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-white mb-6">Upload Photos</h1>

    <div
      class="border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300"
      :class="isDragging
        ? 'border-accent bg-accent/10 shadow-xl shadow-accent/20 scale-[1.02]'
        : 'border-white/10 hover:border-accent/40 hover:bg-white/[0.02] hover:shadow-lg hover:shadow-accent/5'"
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
        <svg class="mx-auto h-12 w-12 mb-4 transition-all duration-300" :class="isDragging ? 'text-accent scale-110 -translate-y-1' : 'text-accent/60'" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
        </svg>
        <p class="text-lg font-medium text-slate-300">Drop images here or click to browse</p>
        <p class="text-sm mt-1 text-slate-500">JPG, PNG, WebP up to 20 MB each</p>
      </div>
    </div>

    <TransitionGroup name="list" tag="div" v-if="files.length" class="mt-6 space-y-2">
      <div
        v-for="(file, i) in files"
        :key="file.name + file.size"
        class="flex items-center justify-between glass-card px-4 py-3 group"
      >
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-8 h-8 rounded-lg bg-accent/10 text-accent flex items-center justify-center shrink-0">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <span class="text-sm font-medium text-slate-300 truncate">{{ file.name }}</span>
          <span class="text-xs text-slate-500 tabular-nums">{{ formatSize(file.size) }}</span>
        </div>
        <button
          @click="removeFile(i)"
          class="text-slate-500 hover:text-red-400 text-lg transition-all duration-150 opacity-0 group-hover:opacity-100 hover:scale-110"
          :disabled="uploading"
        >&times;</button>
      </div>
    </TransitionGroup>

    <div v-if="uploading && uploadProgress > 0" class="mt-4">
      <div class="w-full bg-surface-400 rounded-full h-1.5 overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-300"
          :class="serverProcessing ? 'bg-accent animate-pulse' : 'bg-gradient-to-r from-accent-dark to-accent-light'"
          :style="{ width: uploadProgress + '%' }"
        ></div>
      </div>
      <p class="text-sm text-slate-500 mt-1.5 text-center">
        <template v-if="serverProcessing">
          <span class="inline-flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 animate-spin text-accent" viewBox="0 0 24 24" fill="none">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Saving to server...
          </span>
        </template>
        <template v-else>{{ uploadProgress }}%</template>
      </p>
    </div>

    <button
      v-if="files.length"
      @click="upload"
      :disabled="uploading"
      class="mt-6 w-full btn-primary py-3 text-base"
    >
      {{ serverProcessing ? 'Saving...' : uploading ? 'Uploading...' : `Upload ${files.length} file${files.length > 1 ? 's' : ''}` }}
    </button>
  </div>
</template>

<style scoped>
.list-enter-active { transition: all 0.2s ease-out; }
.list-leave-active { transition: all 0.15s ease-in; }
.list-enter-from { opacity: 0; transform: translateY(-8px); }
.list-leave-to { opacity: 0; transform: translateX(16px); }
.list-move { transition: transform 0.2s ease; }
</style>
