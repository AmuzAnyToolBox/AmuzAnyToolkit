<script setup>
import {ref,watch,onBeforeUnmount} from 'vue'
import {t,number} from './i18n.js'
const props=defineProps({active:Boolean,renderTime:Number,backend:Boolean,serverMetrics:Object})
const blocked=ref(null),heap=ref(null)
function remainingLabel(value){
  if(!Number.isFinite(value)||value<0)return '—'
  const seconds=Math.ceil(value)
  return `≈ ${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`
}
let observer=null,timer=0,tasks=[],started=0
function sample(){
  const now=performance.now(),start=Math.max(started,now-2000)
  tasks=tasks.filter(task=>task.end>start)
  if(observer){
    const busy=tasks.reduce((sum,task)=>sum+Math.max(0,Math.min(now,task.end)-Math.max(start,task.start)),0)
    blocked.value=Math.min(100,100*busy/Math.max(1,now-start))
  }
  const bytes=performance.memory?.usedJSHeapSize
  heap.value=Number.isFinite(bytes)?bytes/1048576:null
}
function stop(){observer?.disconnect();observer=null;clearInterval(timer);tasks=[];blocked.value=null;heap.value=null}
watch(()=>props.active&&!props.backend,active=>{
  stop()
  if(!active)return
  started=performance.now()
  if(typeof PerformanceObserver!=='undefined'&&PerformanceObserver.supportedEntryTypes?.includes('longtask')){
    try{observer=new PerformanceObserver(list=>{for(const entry of list.getEntries())tasks.push({start:entry.startTime,end:entry.startTime+entry.duration})});observer.observe({type:'longtask'});blocked.value=0}catch{observer=null}
  }
  sample();timer=setInterval(sample,1000)
},{immediate:true})
onBeforeUnmount(stop)
</script>
<template>
  <div class="browser-statusbar">
    <div v-if="backend" class="browser-metrics server-metrics" :aria-label="t('Метрики бэкенда')">
      <span :title="t('CPU процесса Python, включая потоки кодирования. 100% — все логические ядра сервера; не весь компьютер.')">{{t('CPU сервера')}}<b>{{serverMetrics?.cpu_percent==null?'—':number(serverMetrics.cpu_percent,{maximumFractionDigits:1})+'%'}}</b></span>
      <span :title="t('Оперативная память процесса Python (RSS), включая обработчик видео.')">{{t('RAM сервера')}}<b>{{serverMetrics?.memory_mb==null?'—':number(serverMetrics.memory_mb,{maximumFractionDigits:0})+' '+t('МБ')}}</b></span>
      <span :title="t('Средняя скорость полного экспорта с момента начала обработки, без ожидания в очереди.')">{{t('Кадров/с')}}<b>{{serverMetrics?.fps?number(serverMetrics.fps,{maximumFractionDigits:1}):'—'}}</b></span>
      <span :title="t('Примерное время до завершения обработки. Оценка уточняется по мере экспорта.')">{{t('Осталось')}}<b>{{remainingLabel(serverMetrics?.eta_seconds)}}</b></span>
    </div>
    <div v-else-if="active" class="browser-metrics" :aria-label="t('Метрики браузера')">
      
      <span :title="t('Время последнего рендера предпросмотра, включая ожидание worker. Это не процент CPU.')">{{t('Рендер')}} <b>{{number(renderTime||0)}} {{t('мс')}}</b></span>
      <span :title="t('Доля последних 2 секунд, занятая задачами основного потока длительностью от 50 мс. Не учитывает worker и GPU.')">{{t('Блокировки')}} <b>{{blocked===null?'—':number(blocked,{maximumFractionDigits:0})+'%'}}</b></span>
      <span :title="t('Используемая память JavaScript. Не включает весь браузер и GPU; доступна не во всех браузерах.')">{{t('JS-память')}} <b>{{heap===null?'—':number(heap,{maximumFractionDigits:0})+' '+t('МБ')}}</b></span>
    </div>
    <a class="repository-link" href="/" :aria-label="t('Все инструменты')" :title="t('Все инструменты')"><svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z"/></svg><span class="repository-name">Toolkit</span></a>
  </div>
</template>
