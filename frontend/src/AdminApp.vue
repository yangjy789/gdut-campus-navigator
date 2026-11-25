<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import axios from 'axios'
import { adminHttp, loginAdmin, setCsrf, whoAmI } from './admin-api'
import { errorMessage } from './api'
import type { PublicPlace } from './campus-api'
const username=ref(''),loginName=ref('admin'),password=ref(''),checking=ref(true),busy=ref(false)
const error=ref(''),success=ref(''),places=ref<PublicPlace[]>([]),query=ref('')
const editing=ref(false),editingId=ref<string|null>(null),deleting=ref<PublicPlace|null>(null)
const form=reactive({id:'',name:'',region:'教学区',category:'学习',aliases:'',planned:false,description:'',x:650,y:650,source_url:'https://www.gdut.edu.cn/info/1715/23413.htm',source_document_url:'',checked_on:'2026-11-24'})
async function load() {places.value=(await adminHttp.get('/campus/places')).data.items}
async function perform(action:()=>Promise<void>) {busy.value=true;error.value='';success.value='';try {await action()} catch(e) {if(axios.isAxiosError(e)&&e.response?.status===401){username.value='';setCsrf('')}error.value=errorMessage(e)} finally {busy.value=false}}
async function login() {await perform(async()=>{try {const result=await loginAdmin(loginName.value,password.value);username.value=result.username;setCsrf(result.csrf_token);await load()} finally {password.value=''}})}
async function logout() {await perform(async()=>{await adminHttp.post('/auth/logout');username.value='';setCsrf('');editing.value=false;deleting.value=null})}
function openPlace(p?:PublicPlace) {
 Object.assign(form,p?{...p,aliases:p.aliases.join('、'),description:p.description??'',x:p.image_position.x,y:p.image_position.y}:{id:'place-'+Date.now().toString(36),name:'',region:'教学区',category:'学习',aliases:'',planned:false,description:'',x:650,y:650,source_url:'https://www.gdut.edu.cn/info/1715/23413.htm',source_document_url:'',checked_on:'2026-11-24'})
 editingId.value=p?.id??null;editing.value=true;deleting.value=null;error.value='';success.value=''
}
async function save() {await perform(async()=>{
 const body={name:form.name,region:form.region,category:form.category,aliases:form.aliases.split(/[、,，]/).map(a=>a.trim()).filter(Boolean),planned:form.planned,description:form.description,image_position:{x:form.x,y:form.y},source_url:form.source_url,source_document_url:form.source_document_url,checked_on:form.checked_on}
 if(editingId.value) await adminHttp.put('/campus/places/'+editingId.value,body)
 else await adminHttp.post('/campus/places',{...body,id:form.id})
 editing.value=false;await load();success.value='地点已保存，访客目录与助手将读取最新信息。'
})}
async function remove() {if(!deleting.value)return;await perform(async()=>{await adminHttp.delete('/campus/places/'+deleting.value!.id);deleting.value=null;await load();success.value='地点已删除。'})}
onMounted(async()=>{try {const me=await whoAmI();username.value=me.username;setCsrf(me.csrf_token);await load()} catch(e) {if(!(axios.isAxiosError(e)&&e.response?.status===401))error.value=errorMessage(e)} finally {checking.value=false}})
</script>
<template>
 <header class="topbar"><a class="brand" href="/"><img class="university-emblem" src="/branding/gdut-emblem.jpg" alt="广东工业大学校徽" width="44" height="44"><span>GDUT <b>Campus</b></span></a><span class="header-caption">校园管理中心</span><a class="admin-home-link" href="/">返回导览</a><el-button v-if="username" :disabled="busy" @click="logout">退出登录</el-button></header>
 <main class="admin-main">
  <p v-if="checking" class="state-card" role="status">正在检查登录状态…</p>
  <form v-else-if="!username" class="panel login-panel" @submit.prevent="login"><p class="eyebrow">CAMPUS ADMINISTRATION</p><h1>管理员登录</h1><p class="muted">维护校园目录、地图位置与信息来源。</p><label>用户名<input v-model="loginName" autocomplete="username" required maxlength="64" :disabled="busy"></label><label>密码<input v-model="password" type="password" autocomplete="current-password" required maxlength="256" :disabled="busy"></label><p v-if="error" class="error-text" role="alert">{{ error }}</p><el-button native-type="submit" type="primary" :loading="busy">登录管理中心</el-button></form>
  <template v-else>
   <div class="admin-intro"><div><p class="eyebrow">CAMPUS CONTENT</p><h1>让校园信息保持鲜活。</h1><p class="muted">当前账号 {{ username }} · 统一校园目录</p></div><div class="admin-counts"><b>{{ places.length }}<small>地点</small></b><b>{{ places.filter(p=>p.planned).length }}<small>规划建筑</small></b></div></div>
   <p v-if="error" class="admin-message error-text" role="alert">{{ error }}</p><p v-if="success" class="admin-message success-text" role="status">{{ success }}</p>
   <div class="admin-toolbar"><el-input v-model="query" placeholder="搜索地点或区域" aria-label="搜索管理地点" clearable style="max-width:320px"/><el-button :disabled="busy" @click="perform(load)">刷新目录</el-button><el-button type="primary" :disabled="busy" @click="openPlace()">新增地点</el-button></div>
   <section v-if="deleting" class="panel delete-confirm" role="alert"><h2>删除“{{ deleting.name }}”？</h2><p>此操作会移除访客目录中的地点，删除前请确认信息已经停用。</p><el-button @click="deleting=null">取消</el-button><el-button type="danger" :loading="busy" @click="remove">确认删除</el-button></section>
   <div class="admin-workspace" :class="{'has-editor':editing}">
    <section class="panel table-panel"><div class="table-scroll"><table><thead><tr><th>地点</th><th>区域</th><th>类别</th><th>状态</th><th>资料日期</th><th>操作</th></tr></thead><tbody><tr v-for="p in places.filter(p=>[p.name,p.region,p.category].join(' ').includes(query.trim()))" :key="p.id"><td>{{ p.name }}</td><td>{{ p.region }}</td><td>{{ p.category }}</td><td>{{ p.planned?'规划中':'已收录' }}</td><td>{{ p.checked_on }}</td><td class="table-actions"><button :disabled="busy" @click="openPlace(p)">编辑</button><button :disabled="busy" class="danger-link" @click="deleting=p;editing=false">删除</button></td></tr></tbody></table></div></section>
    <form v-if="editing" class="panel admin-editor" @submit.prevent="save"><div class="section-heading"><h2>{{ editingId?'编辑地点':'新增地点' }}</h2><button type="button" class="text-button" @click="editing=false">取消</button></div><fieldset :disabled="busy">
     <label>稳定标识<input v-model="form.id" pattern="[a-z][a-z0-9-]*" maxlength="64" required :disabled="!!editingId"></label><label>地点名称<input v-model="form.name" maxlength="100" required></label>
     <label>所属区域<select v-model="form.region"><option v-for="r in ['教学区','生活东区','生活西区']" :key="r">{{ r }}</option></select></label><label>类别<select v-model="form.category"><option v-for="c in ['学习','科研','生活','服务','运动','文化','景观','出入口']" :key="c">{{ c }}</option></select></label>
     <label>旧称与别名<input v-model="form.aliases" placeholder="多个名称以顿号分隔"></label><label>导览介绍<textarea v-model="form.description" rows="4" maxlength="3000"></textarea></label><label class="checkbox-label"><input v-model="form.planned" type="checkbox">规划中的建筑</label>
     <div class="coordinate-fields"><label>图上横坐标<input v-model.number="form.x" type="number" min="0" max="1317" required></label><label>图上纵坐标<input v-model.number="form.y" type="number" min="0" max="2000" required></label></div><p class="field-hint">位置用于校园示意图标记，不作为经纬度。</p>
     <label>资料来源链接<input v-model="form.source_url" type="url" required></label><label>地图或文档链接<input v-model="form.source_document_url" type="url" required></label><label>资料日期<input v-model="form.checked_on" type="date" required></label><el-button type="primary" native-type="submit" :loading="busy">保存地点</el-button>
    </fieldset></form>
   </div>
  </template>
 </main>
</template>
