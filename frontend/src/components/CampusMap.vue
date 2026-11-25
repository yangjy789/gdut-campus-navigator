<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import L from 'leaflet'
import type { Place, Road, Route } from '../api'
import { demoLayout, displayName } from '../demo-layout'

const props = defineProps<{ places: Place[]; roads: Road[]; route: Route | null; selectedId: number | null }>()
const emit = defineEmits<{ select: [id: number] }>()
const container = ref<HTMLDivElement>()
let map: L.Map | undefined
let layers: L.LayerGroup | undefined
let observer: ResizeObserver | undefined
function positions() {
  let extra = 0
  return new Map(props.places.map(p => {
    const point = demoLayout[p.code] ?? ([-120 - Math.floor(extra / 4) * 230, 180 + (extra++ % 4) * 260] as [number,number])
    return [p.id, point] as const
  }))
}
function fit() {
  const points = [...positions().values()]
  map?.fitBounds(L.latLngBounds([[0,0], [760,1140], ...points]), { padding: [35,35] })
}
function draw() {
  if (!map || !layers) return
  layers.clearLayers()
  const points = positions()
  for (const road of props.roads) {
    const a = points.get(road.start_id), b = points.get(road.end_id)
    if (a && b) L.polyline([a, b], { color: '#b0bfb8', weight: 3, dashArray: '5 7' }).addTo(layers)
  }
  for (const segment of props.route?.segments ?? []) {
    const a = points.get(segment.start_id), b = points.get(segment.end_id)
    if (a && b) L.polyline([a, b], { color: '#17634a', weight: 7, opacity: 0.95 }).addTo(layers)
  }
  const routeIds = new Set(props.route?.path.map(p => p.id))
  for (const place of props.places) {
    const position = points.get(place.id)
    if (!position) continue
    const selected = props.selectedId === place.id
    const node = document.createElement('div')
    node.className = `map-label ${routeIds.has(place.id) ? 'on-route' : ''} ${selected ? 'selected' : ''}`
    node.textContent = displayName(place)
    const icon = L.divIcon({ html: node, className: 'map-pin', iconSize: [120, 38], iconAnchor: [60, 19] })
    L.marker(position, { icon, title: node.textContent, keyboard: true }).on('click', () => emit('select', place.id)).addTo(layers)
  }
}
onMounted(() => {
  map = L.map(container.value!, { crs: L.CRS.Simple, minZoom: -3, maxZoom: 2, zoomSnap: 0.1, attributionControl: false, zoomControl: false })
  L.control.zoom({ position: 'bottomright' }).addTo(map)
  layers = L.layerGroup().addTo(map)
  fit(); draw()
  observer = new ResizeObserver(() => { map?.invalidateSize(); fit() })
  observer.observe(container.value!)
})
watch(() => [props.places, props.roads, props.route, props.selectedId], draw)
onBeforeUnmount(() => { observer?.disconnect(); map?.remove() })
</script>

<template>
  <section class="map-shell" aria-label="校园道路关系示意图">
    <div ref="container" class="campus-map"></div>
    <div class="map-caption"><span>道路关系示意图</span><small>人工排布 · 非真实地理位置</small></div>
    <button class="fit-button" @click="fit">显示全图</button>
    <div class="map-legend"><i></i>示例道路 <i class="active"></i>规划路线</div>
  </section>
</template>
