<script setup>
const props = defineProps({
  images: { type: Array, required: true },
  selectedId: { type: Number, default: null },
})

const emit = defineEmits(['select', 'delete'])

function statusColor(status) {
  switch (status) {
    case 'pending':
      return 'bg-gray-400'
    case 'annotated':
      return 'bg-yellow-500'
    case 'processed':
      return 'bg-green-500'
    case 'error':
      return 'bg-red-500'
    default:
      return 'bg-gray-400'
  }
}
</script>

<template>
  <div class="flex flex-col gap-2">
    <div
      v-for="image in images"
      :key="image.id"
      class="relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-colors"
      :class="selectedId === image.id ? 'border-blue-500' : 'border-transparent hover:border-gray-300'"
      @click="emit('select', image.id)"
    >
      <img
        :src="`/api/images/${image.id}/original`"
        :alt="image.filename"
        class="w-full aspect-video object-cover"
        loading="lazy"
      />
      <div class="absolute top-1 right-1 flex gap-1">
        <span
          class="text-[10px] text-white px-1.5 py-0.5 rounded-full capitalize"
          :class="statusColor(image.status)"
        >
          {{ image.status }}
        </span>
      </div>
      <button
        @click.stop="emit('delete', image.id)"
        class="absolute top-1 left-1 w-5 h-5 bg-black/50 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
        title="Delete"
      >
        &times;
      </button>
      <div class="absolute bottom-0 left-0 right-0 bg-black/50 px-1.5 py-0.5">
        <span class="text-[10px] text-white truncate block">{{ image.filename }}</span>
      </div>
    </div>
  </div>
</template>
