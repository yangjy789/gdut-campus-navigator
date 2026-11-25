<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import L from 'leaflet'
import CampusAssistant from './CampusAssistant.vue'
import { errorMessage } from '../api'
import { planNavigation, type PublicPlace, type NavigationPlan } from '../campus-api'
interface Dataset {
  campus:string; places:PublicPlace[]; limitations:string[]; attribution:string;
  map:{width:number;height:number;image_url:string}; sources:{title:string;url:string;published_on?:string}[]
}
const data=ref<Dataset|null>(null), error=ref(''), loading=ref(true)
const query=ref(''), region=ref('全部'), showPlanned=ref(false), selectedId=ref('library')
const start=ref('south-gate'), end=ref('library'), planning=ref(false), routeError=ref(''), navigation=ref<NavigationPlan|null>(null)
const favorites=ref<string[]>([]), favoriteOnly=ref(false)
try { const stored=JSON.parse(localStorage.getItem('gdut-campus-favorites') ?? '[]'); if(Array.isArray(stored)) favorites.value=stored.filter((id:unknown)=>typeof id==='string') } catch { /* 浏览器存储不可用时仍可正常探索 */ }
const container=ref<HTMLDivElement>()
let map:L.Map|undefined, markers:L.LayerGroup|undefined, observer:ResizeObserver|undefined
let navigationVersion=0
const selected=computed(()=>data.value?.places.find(p=>p.id===selectedId.value))
const filtered=computed(()=>data.value?.places.filter(p=>
  (!favoriteOnly.value || favorites.value.includes(p.id)) &&
  (showPlanned.value || !p.planned) && (region.value==='全部' || p.region===region.value) &&
  [p.name,p.category,...p.aliases].join(' ').toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase())) ?? [])
function point(p:PublicPlace):L.LatLngTuple { return [data.value!.map.height-p.image_position.y,p.image_position.x] }
function fit() { if(data.value) map?.fitBounds([[data.value.map.height-1330,0],[data.value.map.height,1317]],{padding:[12,12]}) }
function draw() {
  if(!markers) return
  markers.clearLayers()
  const visible=new Map(filtered.value.map(p=>[p.id,p]))
  if(navigation.value) {visible.set(navigation.value.start.id,navigation.value.start);visible.set(navigation.value.end.id,navigation.value.end)}
  for(const p of visible.values()) {
    const active=p.id===selectedId.value
    const label=document.createElement('span'); label.textContent=p.name+(p.planned?'（规划）':'')
    const endpoint=navigation.value?.start.id===p.id || navigation.value?.end.id===p.id
    L.circleMarker(point(p),{radius:active||endpoint?9:5,color:endpoint?'#b44d2e':active?'#995f16':'#17634a',weight:2,
      fillColor:active?'#ffce78':'#fff',fillOpacity:0.95})
      .bindTooltip(label,{permanent:active,direction:'top',offset:[0,-7]})
      .on('click',()=>choose(p)).addTo(markers)
  }
}
function choose(p:PublicPlace) { selectedId.value=p.id; map?.panTo(point(p)) }
function toggleFavorite(id:string) {
  favorites.value=favorites.value.includes(id)?favorites.value.filter(x=>x!==id):[...favorites.value,id]
  try {localStorage.setItem('gdut-campus-favorites',JSON.stringify(favorites.value))} catch {routeError.value='当前浏览器无法保存收藏，关闭页面后可能丢失。'}
}
function showNavigation(plan:NavigationPlan) {navigationVersion++;planning.value=false;navigation.value=plan;start.value=plan.start.id;end.value=plan.end.id;selectedId.value=plan.end.id;map?.fitBounds(L.latLngBounds([point(plan.start),point(plan.end)]),{padding:[70,70],maxZoom:0});draw()}
async function plan() {
  planning.value=true;routeError.value='';navigation.value=null
  const version=++navigationVersion
  try {const result=await planNavigation(start.value,end.value);if(version===navigationVersion)showNavigation(result)} catch(e) {if(version===navigationVersion)routeError.value=errorMessage(e)} finally {if(version===navigationVersion)planning.value=false}
}
watch([start,end],()=>{navigationVersion++;planning.value=false;routeError.value='';if(navigation.value && (navigation.value.start.id!==start.value || navigation.value.end.id!==end.value)) navigation.value=null})
async function load() {
  loading.value=true; error.value=''
  try {
    data.value=(await axios.get<Dataset>('/api/campus/real',{timeout:15000})).data
    loading.value=false; await nextTick()
    if(!container.value) return
    map=L.map(container.value,{crs:L.CRS.Simple,minZoom:-3,maxZoom:2,zoomSnap:0.1,scrollWheelZoom:false})
    const {width,height,image_url}=data.value.map
    L.imageOverlay(image_url,[[0,0],[height,width]],{attribution:'广东工业大学官方校园示意图'}).addTo(map)
    markers=L.layerGroup().addTo(map); fit(); draw()
    observer=new ResizeObserver(()=>map?.invalidateSize()); observer.observe(container.value)
  } catch(e) { error.value=errorMessage(e); loading.value=false }
}
watch([filtered,selectedId,navigation],draw)
onMounted(load)
onBeforeUnmount(()=>{observer?.disconnect(); map?.remove()})
</script>

<template>
  <main id="campus-explore" class="real-campus">
    <div class="intro"><div><p class="eyebrow">EXPLORE · CONNECT · DISCOVER</p><h1>发现校园，连接每一站。</h1><p>探索大学城校区，收藏心仪地点，开启下一段校园旅程。</p></div><div class="intro-note"><b>广东工业大学 · 大学城校区</b><span>地点探索 / 步行地图 / AI 问答</span></div></div>
    <div v-if="loading" class="state-card" role="status">正在加载官方校园资料…</div>
    <div v-else-if="error" class="state-card" role="alert"><p>{{ error }}</p><el-button @click="load">重新加载</el-button></div>
    <template v-else-if="data">
      <div class="source-notice"><b>{{ data.places.filter(p=>!p.planned).length }} 处校园地点</b><span>三大校园区域 · 名称与地图来源可追溯 · 支持智能问路</span><a :href="data.sources[0]!.url" target="_blank" rel="noopener noreferrer">校园资讯 ↗</a></div>
      <div class="workspace">
        <aside class="sidebar">
          <section class="panel explore-panel"><div class="section-heading"><h2>校园地点</h2><span>{{ filtered.length }} 处</span></div>
            <el-input v-model="query" placeholder="搜索地点、类别或旧名称" aria-label="搜索官方校园地点" clearable />
            <div class="filters" aria-label="校园区域"><button v-for="r in ['全部','教学区','生活东区','生活西区']" :key="r" :class="{active:region===r}" @click="region=r">{{ r }}</button></div>
            <div class="catalog-options"><label class="planned-toggle"><input v-model="favoriteOnly" type="checkbox" />我的收藏</label><label class="planned-toggle"><input v-model="showPlanned" type="checkbox" />显示规划建筑</label></div>
            <div class="place-list official-list"><button v-for="p in filtered" :key="p.id" class="place-row" :class="{chosen:selectedId===p.id}" @click="choose(p)"><span><b>{{ p.name }}{{ p.planned?' · 规划':'' }}</b><small>{{ p.region }}</small></span><span class="place-category">{{ p.category }}</span></button><p v-if="!filtered.length" class="empty-text">没有找到地点；未收录不代表校园内不存在。</p></div>
          </section>
          <section class="panel route-panel"><div class="section-heading"><h2>步行路线</h2><span>百度地图</span></div><label for="campus-start">从哪里出发</label><el-select id="campus-start" v-model="start" aria-label="步行起点" filterable><el-option v-for="p in data.places.filter(p=>!p.planned)" :key="p.id" :value="p.id" :label="p.name" /></el-select><div class="end-label"><label for="campus-end">想去哪里</label><button @click="[start,end]=[end,start]">交换</button></div><el-select id="campus-end" v-model="end" aria-label="步行终点" filterable><el-option v-for="p in data.places.filter(p=>!p.planned)" :key="p.id" :value="p.id" :label="p.name" /></el-select><el-button type="primary" class="plan-button" :loading="planning" :disabled="start===end" @click="plan">查询步行路线</el-button><p v-if="routeError" class="error-text" role="alert">{{ routeError }}</p><p class="real-copy">在地图服务中核对具体位置、步行距离与通行情况。</p></section>
        </aside>
        <div class="main-column">
          <section class="official-map-shell" aria-label="2026年官方校园示意图"><div ref="container" class="official-map"></div><button class="fit-button" @click="fit">显示校园全图</button></section>
          <section v-if="navigation" class="panel" aria-live="polite"><p class="eyebrow">YOUR NEXT STOP</p><h2>{{ navigation.start.name }} → {{ navigation.end.name }}</h2><p class="real-copy">{{ navigation.message }}</p><a class="navigation-link" :href="navigation.navigation_url" target="_blank" rel="noopener noreferrer">在百度地图查看步行路线 ↗</a></section>
          <section v-if="selected" class="panel details" aria-live="polite"><div class="section-heading"><h2>{{ selected.name }} <small>{{ selected.planned?'规划中':selected.region+' · '+selected.category }}</small></h2><button class="text-button" :aria-pressed="favorites.includes(selected.id)" @click="toggleFavorite(selected.id)">{{ favorites.includes(selected.id)?'★ 已收藏':'☆ 收藏地点' }}</button></div><p v-if="selected.description">{{ selected.description }}</p><p v-if="selected.aliases.length">旧称或命名范围：{{ selected.aliases.join('、') }}</p><div v-if="!selected.planned" class="detail-actions"><el-button @click="start=selected.id">设为起点</el-button><el-button @click="end=selected.id">设为终点</el-button></div><details class="place-provenance"><summary>地点资料与位置说明</summary><p class="muted">地图标记为近似图上位置，不是 GPS 坐标或建筑入口。资料日期 {{ selected.checked_on }}。</p><div class="source-links"><a :href="selected.source_url" target="_blank" rel="noopener noreferrer">学校公告 ↗</a><a :href="selected.source_document_url" target="_blank" rel="noopener noreferrer">校园地图 ↗</a></div></details></section>
          <CampusAssistant @navigation="showNavigation" />
        </div>
      </div>
      <footer><span>{{ data.attribution }}</span><span>GDUT CAMPUS · 独立校园导览平台</span></footer>
    </template>
  </main>
</template>

<style scoped>
.source-notice{display:flex;align-items:center;gap:16px;margin:0 0 22px;padding:16px 20px;background:#e9f1e8;border:1px solid #cbdcc9;border-radius:12px;font-size:13px;line-height:1.8;color:#46634b}.source-notice b{white-space:nowrap;color:#17634a}.source-notice a{white-space:nowrap;margin-left:auto;color:#17634a}.official-map-shell{position:relative;height:680px;border:1px solid #d9e5dc;border-radius:14px;overflow:hidden}.official-map{width:100%;height:100%;background:#f4f5f1}.official-list{max-height:550px}.official-list .place-row{justify-content:space-between}.planned-toggle{display:flex;gap:7px;align-items:center;font-size:11px;color:#6b796b;margin:10px 0 15px}.real-copy{font-size:14px;color:#6d7f70;line-height:1.8}.official-badge{font-size:12px;background:#edf4ea;color:#17634a;padding:6px 10px;border-radius:6px;white-space:nowrap}.source-links{display:flex;gap:20px;font-size:13px}.source-links a{color:#17634a}.official-map :deep(.leaflet-tooltip){font:600 13px/1.5 inherit;border-color:#d2dfce}.official-map :deep(.leaflet-control-attribution){font-size:10px}@media(max-width:720px){.source-notice{align-items:flex-start;flex-direction:column;gap:5px}.source-notice a{margin:0}.official-map-shell{height:490px}.official-list{max-height:240px}.source-links{flex-wrap:wrap;gap:10px}}
</style>
