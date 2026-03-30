<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import api from '../api.js'
import PlateOverlay from './PlateOverlay.vue'

const props = defineProps({
  image: { type: Object, required: true },
})

const emit = defineEmits(['plateSaved', 'saveAndNext'])

const canvasRef = ref(null)
const containerRef = ref(null)
const imgEl = ref(null)

const points = ref([])
const redactMode = ref('white')
const zoom = ref(1)
const panOffset = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })
const imageLoaded = ref(false)
const naturalWidth = ref(0)
const naturalHeight = ref(0)

const scale = computed(() => {
  if (!containerRef.value || !naturalWidth.value) return 1
  const containerWidth = containerRef.value.clientWidth
  const containerHeight = containerRef.value.clientHeight - 60
  const scaleX = containerWidth / naturalWidth.value
  const scaleY = containerHeight / naturalHeight.value
  return Math.min(scaleX, scaleY, 1) * zoom.value
})

const displayWidth = computed(() => naturalWidth.value * scale.value)
const displayHeight = computed(() => naturalHeight.value * scale.value)

function onImageLoad(e) {
  naturalWidth.value = e.target.naturalWidth
  naturalHeight.value = e.target.naturalHeight
  imageLoaded.value = true
  zoom.value = 1
  panOffset.value = { x: 0, y: 0 }
  nextTick(drawCanvas)
}

function drawCanvas() {
  const canvas = canvasRef.value
  if (!canvas || !imageLoaded.value) return
  const ctx = canvas.getContext('2d')

  canvas.width = displayWidth.value
  canvas.height = displayHeight.value

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  // Draw existing plates
  if (props.image.plates) {
    for (const plate of props.image.plates) {
      drawQuad(ctx, plate.corners, 'rgba(255, 0, 0, 0.2)', 'rgba(255, 0, 0, 0.7)')
    }
  }

  // Draw current points
  if (points.value.length > 0) {
    ctx.beginPath()
    ctx.strokeStyle = '#3b82f6'
    ctx.lineWidth = 2
    const first = points.value[0]
    ctx.moveTo(first[0] * scale.value, first[1] * scale.value)
    for (let i = 1; i < points.value.length; i++) {
      ctx.lineTo(points.value[i][0] * scale.value, points.value[i][1] * scale.value)
    }
    if (points.value.length === 4) {
      ctx.closePath()
      ctx.fillStyle = 'rgba(59, 130, 246, 0.2)'
      ctx.fill()
    }
    ctx.stroke()

    // Draw point markers
    for (const pt of points.value) {
      ctx.beginPath()
      ctx.arc(pt[0] * scale.value, pt[1] * scale.value, 5, 0, Math.PI * 2)
      ctx.fillStyle = '#3b82f6'
      ctx.fill()
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 1.5
      ctx.stroke()
    }
  }
}

function drawQuad(ctx, corners, fillColor, strokeColor) {
  ctx.beginPath()
  ctx.moveTo(corners[0][0] * scale.value, corners[0][1] * scale.value)
  for (let i = 1; i < corners.length; i++) {
    ctx.lineTo(corners[i][0] * scale.value, corners[i][1] * scale.value)
  }
  ctx.closePath()
  ctx.fillStyle = fillColor
  ctx.fill()
  ctx.strokeStyle = strokeColor
  ctx.lineWidth = 2
  ctx.stroke()
}

function onCanvasClick(e) {
  if (points.value.length >= 4) return

  const rect = canvasRef.value.getBoundingClientRect()
  const cssX = e.clientX - rect.left
  const cssY = e.clientY - rect.top

  // Convert to natural image coordinates
  const realX = cssX / scale.value
  const realY = cssY / scale.value

  points.value.push([Math.round(realX * 100) / 100, Math.round(realY * 100) / 100])

  if (points.value.length === 4) {
    // Auto-save after 4th point
    nextTick(drawCanvas)
  } else {
    drawCanvas()
  }
}

function undoPoint() {
  points.value.pop()
  drawCanvas()
}

async function savePlate() {
  if (points.value.length !== 4) return

  await api.post(`/images/${props.image.id}/plates`, {
    corners: points.value,
    redact_mode: redactMode.value,
  })

  points.value = []
  emit('plateSaved')
  nextTick(drawCanvas)
}

function onWheel(e) {
  e.preventDefault()
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  zoom.value = Math.max(0.5, Math.min(5, zoom.value * delta))
  nextTick(drawCanvas)
}

function onMouseDown(e) {
  if (e.button === 1 || (e.shiftKey && e.button === 0)) {
    e.preventDefault()
    isPanning.value = true
    panStart.value = { x: e.clientX - panOffset.value.x, y: e.clientY - panOffset.value.y }
  }
}

function onMouseMove(e) {
  if (isPanning.value) {
    panOffset.value = {
      x: e.clientX - panStart.value.x,
      y: e.clientY - panStart.value.y,
    }
  }
}

function onMouseUp() {
  isPanning.value = false
}

function resetView() {
  zoom.value = 1
  panOffset.value = { x: 0, y: 0 }
  nextTick(drawCanvas)
}

watch(() => props.image, () => {
  points.value = []
  imageLoaded.value = false
  zoom.value = 1
  panOffset.value = { x: 0, y: 0 }
})

watch(() => [props.image.plates, scale.value], () => {
  nextTick(drawCanvas)
}, { deep: true })

onMounted(() => {
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('mousemove', onMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('mousemove', onMouseMove)
})
</script>

<template>
  <div class="flex flex-col h-full" ref="containerRef">
    <!-- Toolbar -->
    <div class="flex items-center gap-3 px-4 py-2 border-b border-gray-200 bg-gray-50 shrink-0">
      <span class="text-sm font-medium text-gray-700 truncate">{{ image.filename }}</span>
      <span
        class="text-xs px-2 py-0.5 rounded-full capitalize"
        :class="{
          'bg-gray-200 text-gray-600': image.status === 'pending',
          'bg-yellow-100 text-yellow-700': image.status === 'annotated',
          'bg-green-100 text-green-700': image.status === 'processed',
          'bg-red-100 text-red-700': image.status === 'error',
        }"
      >
        {{ image.status }}
      </span>

      <div class="flex-1"></div>

      <label class="flex items-center gap-1.5 text-sm text-gray-600">
        Mode:
        <select v-model="redactMode" class="text-sm border rounded px-2 py-1">
          <option value="white">White Fill</option>
          <option value="blur">Blur</option>
        </select>
      </label>

      <button
        @click="undoPoint"
        :disabled="!points.length"
        class="text-sm px-3 py-1 border rounded text-gray-600 hover:bg-gray-100 disabled:opacity-30"
      >
        Undo Point
      </button>

      <button
        @click="savePlate"
        :disabled="points.length !== 4"
        class="text-sm px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-30"
      >
        Save Plate
      </button>

      <button
        @click="resetView"
        class="text-sm px-3 py-1 border rounded text-gray-600 hover:bg-gray-100"
      >
        Reset Zoom
      </button>

      <button
        @click="emit('saveAndNext')"
        class="text-sm px-3 py-1 bg-gray-800 text-white rounded hover:bg-gray-900"
      >
        Next &rarr;
      </button>
    </div>

    <!-- Canvas area -->
    <div
      class="flex-1 overflow-hidden flex items-center justify-center bg-gray-100 relative"
      @wheel.prevent="onWheel"
      @mousedown="onMouseDown"
    >
      <div
        class="relative"
        :style="{
          transform: `translate(${panOffset.x}px, ${panOffset.y}px)`,
        }"
      >
        <img
          ref="imgEl"
          :src="`/api/images/${image.id}/original`"
          :alt="image.filename"
          class="block max-w-none"
          :style="{ width: displayWidth + 'px', height: displayHeight + 'px' }"
          @load="onImageLoad"
          draggable="false"
        />
        <canvas
          ref="canvasRef"
          class="absolute top-0 left-0 cursor-crosshair"
          :width="displayWidth"
          :height="displayHeight"
          :style="{ width: displayWidth + 'px', height: displayHeight + 'px' }"
          @click="onCanvasClick"
        />
        <PlateOverlay
          v-if="image.plates"
          :plates="image.plates"
          :scale="scale"
          @deleted="emit('plateSaved')"
        />
      </div>

      <!-- Instructions -->
      <div
        v-if="points.length < 4"
        class="absolute bottom-3 left-1/2 -translate-x-1/2 bg-black/70 text-white text-sm px-4 py-2 rounded-lg"
      >
        Click corner {{ points.length + 1 }} of 4
        <span class="text-white/60 ml-2">
          (TL &rarr; TR &rarr; BR &rarr; BL)
        </span>
      </div>
      <div
        v-else-if="points.length === 4"
        class="absolute bottom-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-sm px-4 py-2 rounded-lg"
      >
        Quad complete — click "Save Plate" or add more detail
      </div>
    </div>
  </div>
</template>
