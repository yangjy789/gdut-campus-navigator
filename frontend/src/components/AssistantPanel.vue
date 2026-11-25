<script setup lang="ts">
import { onMounted, ref } from 'vue'
import axios from 'axios'
import { errorMessage, type Route } from '../api'
defineProps<{ knowledgeOnly?:boolean }>()

interface Source { id:string; title:string; content:string; source_url:string|null; source_type:'official'|'project'; verified_on:string }
interface Answer { answer:string; status:'answered'|'insufficient_evidence'; sources:Source[]; model:string|null }
interface RoutePlan { status:'planned'|'need_clarification'|'no_route'; message:string; start_place:string|null; end_place:string|null; route:Route|null; model:string|null; tool_used:boolean; extraction_method:'model_tool'|'explicit_pattern'|'none' }

const emit = defineEmits<{ routePlanned: [route: Route]; clearRoute: [] }>()

const mode = ref<'knowledge'|'route'>('knowledge')
const question = ref(''), answer = ref<Answer|null>(null), asked = ref('')
const routeQuestion = ref(''), routeResult = ref<RoutePlan|null>(null), routeAsked = ref('')
const busy=ref(false), error=ref(''), configured=ref(false), count=ref(0), checking=ref(true)
const provider=ref('硅基流动'), model=ref('XingChenAGI/Xing4.0-29B')
const routeSamples = ['从北门到食堂怎么走', '我想从图书馆去运动场', '从宿舍区到行政楼']
async function check() {
  checking.value=true
  try { const {data}=await axios.get('/api/assistant/status',{timeout:30000}); configured.value=data.configured; count.value=data.document_count; provider.value=data.provider; model.value=data.model }
  catch(e) { error.value=errorMessage(e) }
  finally { checking.value=false }
}
async function ask() {
  if (question.value.trim().length<2 || busy.value) return
  busy.value=true; error.value=''; answer.value=null; asked.value=question.value.trim()
  try { answer.value=(await axios.post<Answer>('/api/assistant/ask',{question:asked.value},{timeout:60000})).data }
  catch(e) { error.value=errorMessage(e) }
  finally { busy.value=false }
}
async function askRoute() {
  if (routeQuestion.value.trim().length<2 || busy.value) return
  busy.value=true; error.value=''; routeResult.value=null; routeAsked.value=routeQuestion.value.trim()
  try {
    const {data}=await axios.post<RoutePlan>('/api/assistant/route',{question:routeAsked.value},{timeout:60000})
    routeResult.value=data
    if (data.status==='planned' && data.route) emit('routePlanned', data.route)
    else emit('clearRoute')
  } catch(e) { error.value=errorMessage(e) }
  finally { busy.value=false }
}
function useSample(text:string) { if (mode.value==='route') routeQuestion.value=text; else question.value=text }
onMounted(check)
</script>

<template>
  <section id="campus-assistant" class="panel assistant-panel">
    <div class="section-heading"><div><p class="eyebrow">CAMPUS KNOWLEDGE</p><h2>校园知识助手</h2></div><span>{{ checking ? '正在检查配置' : configured ? `${provider} · ${model}` : `${provider} · 待配置密钥` }}</span></div>

    <div v-if="!knowledgeOnly" class="mode-switch" aria-label="助手模式">
      <button :class="{ active: mode==='knowledge' }" :aria-pressed="mode==='knowledge'" @click="mode='knowledge'">知识问答</button>
      <button :class="{ active: mode==='route' }" :aria-pressed="mode==='route'" @click="mode='route'">AI 规划路线 <small>工具调用</small></button>
    </div>

    <template v-if="mode==='knowledge'">
      <p class="assistant-description">先查资料，再给答案。依据 {{ count }} 条已整理资料回答，并附上来源。</p>
      <div class="question-suggestions"><button v-for="sample in ['大学城校区的地址是什么？','官方校园地图在哪里查看？','示意图能用于真实导航吗？']" :key="sample" :disabled="busy" @click="useSample(sample)">{{ sample }}</button></div>
      <form @submit.prevent="ask"><label class="question-label" for="campus-question">你的问题</label><textarea id="campus-question" v-model="question" rows="3" minlength="2" maxlength="600" required :disabled="busy" placeholder="例如：大学城校区有哪些官方地图资料？"></textarea><div class="question-actions"><small>{{ busy ? '模型繁忙时会自动重试，请勿重复发送。' : `${question.length}/600 · 问题与检索资料将发送至${provider}` }}</small><el-button type="primary" native-type="submit" :loading="busy" :disabled="question.trim().length<2 || checking">{{ busy ? '正在查阅与回答' : '发送问题' }}</el-button></div></form>
      <p v-if="!checking && !configured" class="field-hint">请由项目管理员完成{{ provider }}配置后重试。<button class="text-button" @click="check">重新检查配置</button></p>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
      <div v-if="answer" class="assistant-answer" aria-live="polite"><p class="asked-question">{{ asked }}</p><span class="answer-label">{{ answer.status==='answered' ? '根据资料回答' : '资料不足' }}</span><p class="answer-text">{{ answer.answer }}</p><div v-if="answer.sources.length" class="answer-sources"><h3>本次引用资料</h3><details v-for="source in answer.sources" :key="source.id"><summary>{{ source.title }} <small>{{ source.source_type==='official' ? '学校官方' : '项目说明' }}</small></summary><p>{{ source.content }}</p><span>核验日期 {{ source.verified_on }}</span><a v-if="source.source_url" :href="source.source_url" target="_blank" rel="noopener noreferrer">查看原始来源</a></details></div></div>
      <p class="assistant-footnote">{{ knowledgeOnly ? '依据官网与项目资料回答，不查询实时开放情况；当前不提供真实校园路线。' : '资料可能有时效限制。当前不查询实时开放情况，不提供真实校园路线；路线规划请使用「AI 规划路线」或左侧表单。' }}</p>
    </template>

    <template v-else>
      <p class="assistant-description">用一句话说出起点和终点，助手只负责识别地点，路线由后端 Dijkstra 在示例道路上真实计算，并在地图高亮。</p>
      <div class="question-suggestions"><button v-for="sample in routeSamples" :key="sample" :disabled="busy" @click="useSample(sample)">{{ sample }}</button></div>
      <form @submit.prevent="askRoute"><label class="question-label" for="route-question">从哪里到哪里</label><textarea id="route-question" v-model="routeQuestion" rows="2" minlength="2" maxlength="300" required :disabled="busy" placeholder="例如：从北门到食堂怎么走？"></textarea><div class="question-actions"><small>{{ busy ? '正在识别地点并计算路线，请勿重复发送。' : `${routeQuestion.length}/300 · 仅地点名称发送给模型` }}</small><el-button type="primary" native-type="submit" :loading="busy" :disabled="routeQuestion.trim().length<2 || checking">{{ busy ? '正在规划' : '规划路线' }}</el-button></div></form>
      <p v-if="!checking && !configured" class="field-hint">请由项目管理员完成{{ provider }}配置后重试。<button class="text-button" @click="check">重新检查配置</button></p>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
      <div v-if="routeResult" class="assistant-answer" aria-live="polite">
        <p class="asked-question">{{ routeAsked }}</p>
        <span class="answer-label">{{ routeResult.status==='planned' ? '路线已规划并同步地图' : routeResult.status==='no_route' ? '无法规划' : '需要补充说明' }}</span>
        <p class="answer-text">{{ routeResult.message }}</p>
        <p v-if="routeResult.extraction_method==='explicit_pattern'" class="field-hint">本次按明确的“从哪里到哪里”句式识别地点。</p>
        <div v-if="routeResult.route" class="route-result">
          <p><b>{{ routeResult.start_place }}</b> → <b>{{ routeResult.end_place }}</b> · <strong>{{ routeResult.route.distance_m }}</strong> 米（示例）</p>
          <p class="route-path">{{ routeResult.route.path.map(p=>p.code).join(' → ') }}</p>
          <button class="text-button" @click="emit('clearRoute')">清除地图高亮</button>
        </div>
      </div>
      <p class="assistant-footnote">模型不返回距离或编号；地点由后端对照真实地点表解析，歧义时会要求澄清。示例数据不能用于真实导航。</p>
    </template>
  </section>
</template>
