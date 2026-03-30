<script setup>
import { getSessionToken } from '../api.js'

const props = defineProps({
  images: { type: Array, required: true },
  selectedId: { type: Number, default: null },
})

const emit = defineEmits(['select', 'delete'])

function statusColor(status) {
  switch (status) {
    case 'pending':
      return 'bg-slate-600 text-slate-300'
    case 'annotated':
      return 'bg-yellow-500/20 text-yellow-400'
    case 'processed':
      return 'bg-accent/20 text-accent-light'
    case 'error':
      return 'bg-red-500/20 text-red-400'
    default:
      return 'bg-slate-600 text-slate-300'
  }
}

function thumbnailUrl(image) {
  const token = getSessionToken()
  return `/api/images/${image.id}/original?session_token=${token}`
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div
      v-for="image in images"
      :key="image.id"
      class="relative group cursor-pointer rounded-xl overflow-hidden border-2 transition-all duration-200"
      :class="selectedId === image.id
        ? 'border-accent shadow-lg shadow-accent/10 scale-[1.03]'
        : 'border-transparent hover:border-white/10 hover:scale-[1.02]'"
      @click="emit('select', image.id)"
    >
      <img
        :src="thumbnailUrl(image)"
        :alt="image.filename"
        class="w-full aspect-video object-cover"
        loading="lazy"
      />
      <div class="absolute top-1 right-1 flex gap-1">
        <span
          class="text-[10px] px-1.5 py-0.5 rounded-full capitalize font-medium backdrop-blur-sm"
          :class="statusColor(image.status)"
        >
          {{ image.status }}
        </span>
      </div>
      <button
        @click.stop="emit('delete', image.id)"
        class="absolute top-1 left-1 w-5 h-5 bg-black/60 backdrop-blur-sm text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center hover:bg-red-500/80"
        title="Delete"
      >
        &times;
      </button>
      <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent px-1.5 py-1">
        <span class="text-[10px] text-white/80 truncate block">{{ image.filename }}</span>
      </div>
    </div>
  </div>
</template>
