<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'
import { errorMessage } from '../api'
import type { NavigationPlan } from '../campus-api'
interface Source { id:string; title:string; content:string; source_url:string|null; source_type:string; verified_on:string }
interface Answer { answer:string; status:string; sources:Source[] }
const emit=defineEmits<{navigation:[plan:NavigationPlan]}>()
const mode=ref<'knowledge'|'route'>('knowledge'), question=ref(''), asked=ref(''), busy=ref(false), error=ref('')
const answer=ref<Answer|null>(null), plan=ref<NavigationPlan|null>(null), message=ref('')
function change(value:'knowledge'|'route') { mode.value=value; question.value=''; answer.value=null; plan.value=null; message.value=''; error.value='' }
async function send() {
  if(busy.value || question.value.trim().length<2) return
  busy.value=true; error.value=''; answer.value=null; plan.value=null; message.value=''; asked.value=question.value.trim()
  try {
    if(mode.value==='knowledge') answer.value=(await axios.post('/api/campus/real/ask',{question:asked.value},{timeout:60000})).data
    else {
      const {data}=await axios.post('/api/campus/real/assistant/route',{question:asked.value},{timeout:60000})
      if(data.status==='navigation_ready') {plan.value=data; emit('navigation',data)}
      else message.value=data.message
    }
  } catch(e) {error.value=errorMessage(e)}
  finally {busy.value=false}
}
</script>
<template>
  <section id="campus-assistant" class="panel assistant-panel">
    <div class="section-heading"><div><p class="eyebrow">CAMPUS INTELLIGENCE</p><h2>你的校园助手</h2></div><span>地点识别 · 有据可查</span></div>
    <div class="mode-switch" aria-label="助手模式"><button :disabled="busy" :class="{active:mode==='knowledge'}" :aria-pressed="mode==='knowledge'" @click="change('knowledge')">校园问答</button><button :disabled="busy" :class="{active:mode==='route'}" :aria-pressed="mode==='route'" @click="change('route')">智能问路</button></div>
    <p class="assistant-description">{{ mode==='knowledge'?'了解校园地点、建筑名称与生活信息，每次回答附上依据。':'说出起点与终点，确认校园地点后衔接步行地图。' }}</p>
    <div class="question-suggestions"><button v-for="sample in mode==='knowledge'?['工大广场原来叫什么？','团结湖在哪里？','校区的地址是什么？']:['从南门到图书馆怎么走？','从图书馆到东一食堂','我在体育馆，想去南门']" :key="sample" :disabled="busy" @click="question=sample">{{ sample }}</button></div>
    <form @submit.prevent="send"><label class="question-label" for="campus-message">{{ mode==='knowledge'?'想了解什么？':'从哪里到哪里？' }}</label><textarea id="campus-message" v-model="question" rows="3" minlength="2" :maxlength="mode==='route'?300:600" required :disabled="busy" :placeholder="mode==='knowledge'?'例如：图书馆位于哪个区域？':'例如：从南门到图书馆怎么走？'"></textarea><div class="question-actions"><small>问题与相关公开资料将发送至硅基流动</small><el-button type="primary" native-type="submit" :loading="busy" :disabled="question.trim().length<2">{{ busy?'正在处理':'发送' }}</el-button></div></form>
    <p v-if="error" class="error-text" role="alert">{{ error }}</p><p v-if="message" class="field-hint" role="status">{{ message }}</p>
    <div v-if="answer" class="assistant-answer" aria-live="polite"><p class="asked-question">{{ asked }}</p><span class="answer-label">{{ answer.status==='answered'?'校园答复':'需要更多资料' }}</span><p class="answer-text">{{ answer.answer }}</p><div v-if="answer.sources.length" class="answer-sources"><h3>信息来源</h3><details v-for="s in answer.sources" :key="s.id"><summary>{{ s.title }} <small>{{ s.source_type==='official'?'学校资料':'平台资料' }}</small></summary><p>{{ s.content }}</p><span>资料日期 {{ s.verified_on }}</span><a v-if="s.source_url" :href="s.source_url" target="_blank" rel="noopener noreferrer">查看来源 ↗</a></details></div></div>
    <div v-if="plan" class="assistant-answer" aria-live="polite"><p class="asked-question">{{ asked }}</p><p class="answer-text">{{ plan.start.name }} → {{ plan.end.name }}</p><p>{{ plan.message }}</p><a class="navigation-link" :href="plan.navigation_url" target="_blank" rel="noopener noreferrer">在百度地图查看步行路线 ↗</a></div>
    <p class="assistant-footnote">开放时间和道路通行情况可能变化，请以学校通知及地图服务的最新信息为准。</p>
  </section>
</template>
