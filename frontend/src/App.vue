<script setup lang="ts">
import RealCampus from './components/RealCampus.vue'
</script>
<template>
  <div class="app-frame">
    <header class="topbar"><a class="brand" href="/" aria-label="校园探索首页"><img class="university-emblem" src="/branding/gdut-emblem.jpg" alt="广东工业大学校徽" width="44" height="44"><span>GDUT <b>Campus</b></span></a><span class="header-caption">校园探索与智能导览</span><nav class="site-nav" aria-label="主导航"><a href="#campus-explore">探索校园</a><a href="#campus-assistant">智能助手</a><a href="/admin">管理中心</a></nav></header>
    <RealCampus />
  </div>
</template>
