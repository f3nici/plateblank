<script setup>
import api from '../api.js'

const props = defineProps({
  plates: { type: Array, required: true },
  scale: { type: Number, required: true },
})

const emit = defineEmits(['deleted'])

async function deletePlate(plateId) {
  await api.delete(`/plates/${plateId}`)
  emit('deleted')
}
</script>

<template>
  <div>
    <div
      v-for="plate in plates"
      :key="plate.id"
      class="absolute"
      :style="{
        left: Math.min(...plate.corners.map(c => c[0])) * scale + 'px',
        top: Math.min(...plate.corners.map(c => c[1])) * scale + 'px',
      }"
    >
      <div class="flex items-center gap-1 bg-surface-400/90 backdrop-blur-sm text-slate-300 text-[10px] px-1.5 py-0.5 rounded-lg border border-white/10 whitespace-nowrap">
        <span>{{ plate.redact_mode }}</span>
        <button
          @click="deletePlate(plate.id)"
          class="text-red-400 hover:text-red-300 ml-1 transition-colors"
          title="Delete plate"
        >
          &times;
        </button>
      </div>
    </div>
  </div>
</template>
