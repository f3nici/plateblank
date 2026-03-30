<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { getSessionToken } from '../api.js'
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

let drawRAF = null

const baseScale = computed(() => {
  if (!containerRef.value || !naturalWidth.value) return 1
  const containerWidth = containerRef.value.clientWidth
  const containerHeight = containerRef.value.clientHeight - 60
  const scaleX = containerWidth / naturalWidth.value
  const scaleY = containerHeight / naturalHeight.value
  return Math.min(scaleX, scaleY, 1)
})

const scale = computed(() => baseScale.value * zoom.value)

const displayWidth = computed(() => naturalWidth.value * scale.value)
const displayHeight = computed(() => naturalHeight.value * scale.value)

function onImageLoad(e) {
  naturalWidth.value = e.target.naturalWidth
  naturalHeight.value = e.target.naturalHeight
  imageLoaded.value = true
  zoom.value = 1
  panOffset.value = { x: 0, y: 0 }
  scheduleRedraw()
}

function scheduleRedraw() {
  if (drawRAF) cancelAnimationFrame(drawRAF)
  drawRAF = requestAnimationFrame(drawCanvas)
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
      drawQuad(ctx, plate.corners, 'rgba(20, 184, 166, 0.15)', 'rgba(20, 184, 166, 0.7)')
    }
  }

  // Draw current points
  if (points.value.length > 0) {
    ctx.beginPath()
    ctx.strokeStyle = '#2dd4bf'
    ctx.lineWidth = 2
    const first = points.value[0]
    ctx.moveTo(first[0] * scale.value, first[1] * scale.value)
    for (let i = 1; i < points.value.length; i++) {
      ctx.lineTo(points.value[i][0] * scale.value, points.value[i][1] * scale.value)
    }
    if (points.value.length === 4) {
      ctx.closePath()
      ctx.fillStyle = 'rgba(45, 212, 191, 0.15)'
      ctx.fill()
    }
    ctx.stroke()

    // Draw point markers
    for (const pt of points.value) {
      ctx.beginPath()
      ctx.arc(pt[0] * scale.value, pt[1] * scale.value, 5, 0, Math.PI * 2)
      ctx.fillStyle = '#14b8a6'
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

  const realX = cssX / scale.value
  const realY = cssY / scale.value

  points.value.push([Math.round(realX * 100) / 100, Math.round(realY * 100) / 100])
  scheduleRedraw()
}

function undoPoint() {
  points.value.pop()
  scheduleRedraw()
}

async function savePlate() {
  if (points.value.length !== 4) return

  await api.post(`/images/${props.image.id}/plates`, {
    corners: points.value,
    redact_mode: redactMode.value,
  })

  points.value = []
  emit('plateSaved')
  nextTick(scheduleRedraw)
}

function onWheel(e) {
  e.preventDefault()
  const container = containerRef.value
  if (!container) return

  const rect = container.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  const oldZoom = zoom.value
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  const newZoom = Math.max(0.5, Math.min(5, oldZoom * delta))

  // Adjust pan so the point under the mouse stays fixed
  const zoomRatio = newZoom / oldZoom
  panOffset.value = {
    x: mouseX - (mouseX - panOffset.value.x) * zoomRatio,
    y: mouseY - (mouseY - panOffset.value.y) * zoomRatio,
  }

  zoom.value = newZoom
  scheduleRedraw()
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
  scheduleRedraw()
}

function imageOriginalUrl() {
  const token = getSessionToken()
  return `/api/images/${props.image.id}/original?session_token=${token}`
}

watch(() => props.image, () => {
  points.value = []
  imageLoaded.value = false
  zoom.value = 1
  panOffset.value = { x: 0, y: 0 }
})

watch(() => [props.image.plates, scale.value], () => {
  scheduleRedraw()
}, { deep: true })

onMounted(() => {
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('mousemove', onMouseMove)
})

onUnmounted(() => {
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('mousemove', onMouseMove)
  if (drawRAF) cancelAnimationFrame(drawRAF)
})
</script>

<template>
  <div class="flex flex-col h-full" ref="containerRef">
    <!-- Toolbar -->
    <div class="flex items-center gap-3 px-4 py-2 border-b border-white/5 bg-surface-400/50 shrink-0">
      <span class="text-sm font-medium text-slate-300 truncate">{{ image.filename }}</span>
      <span
        class="text-xs px-2 py-0.5 rounded-full capitalize font-medium"
        :class="{
          'bg-slate-700 text-slate-400': image.status === 'pending',
          'bg-yellow-500/20 text-yellow-400': image.status === 'annotated',
          'bg-accent/20 text-accent-light': image.status === 'processed',
          'bg-red-500/20 text-red-400': image.status === 'error',
        }"
      >
        {{ image.status }}
      </span>

      <div class="flex-1"></div>

      <label class="flex items-center gap-1.5 text-sm text-slate-400">
        <select v-model="redactMode" class="text-sm bg-surface-300 border border-white/10 rounded-lg px-2.5 py-1 text-slate-300 focus:outline-none focus:border-accent/40">
          <option value="white">White Fill</option>
          <option value="blur">Blur</option>
        </select>
      </label>

      <button
        @click="undoPoint"
        :disabled="!points.length"
        class="btn-secondary text-xs px-3 py-1.5"
      >
        Undo
      </button>

      <button
        @click="savePlate"
        :disabled="points.length !== 4"
        class="btn-primary text-xs px-3 py-1.5"
      >
        Save Plate
      </button>

      <button
        @click="resetView"
        class="btn-secondary text-xs px-3 py-1.5"
      >
        Reset Zoom
      </button>

      <button
        @click="emit('saveAndNext')"
        class="btn-secondary text-xs px-3 py-1.5"
      >
        Next &rarr;
      </button>
    </div>

    <!-- Canvas area -->
    <div
      class="flex-1 overflow-hidden flex items-center justify-center bg-surface-500 relative"
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
          :src="imageOriginalUrl()"
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
        class="absolute bottom-3 left-1/2 -translate-x-1/2 bg-surface-400/90 backdrop-blur-sm text-slate-300 text-sm px-4 py-2 rounded-xl border border-white/10"
      >
        Click corner {{ points.length + 1 }} of 4
        <span class="text-slate-500 ml-2">
          (TL &rarr; TR &rarr; BR &rarr; BL)
        </span>
      </div>
      <div
        v-else-if="points.length === 4"
        class="absolute bottom-3 left-1/2 -translate-x-1/2 bg-accent/90 backdrop-blur-sm text-white text-sm px-4 py-2 rounded-xl"
      >
        Quad complete &mdash; click "Save Plate" or add more detail
      </div>
    </div>
  </div>
</template>
