import {reactive,watch} from 'vue'

import {themes,accentText} from '../../../../ui-kit/themes.js'
export {themes,accentText}
export const preferenceDefaults={locale:'ru',theme:'paper',accent:'#62734a',density:'comfortable',fontScale:100,panelWidth:340,radius:8,grid:false,imageFormat:'png',exportQuality:92,fileName:'AmuzASCII',videoFormat:'mp4'}
const locales=['ru','en'],formats=['png','jpeg','webp','svg','txt','html']
export function sanitizePreferences(input={}){
  if(!input||typeof input!=='object')input={}
  const clean={...preferenceDefaults}
  if(['webm-vp9','webm-vp8'].includes(input.videoFormat))clean.videoFormat='webm'
  for(const [key,allowed] of [['locale',locales],['theme',themes.map(t=>t.id)],['density',['comfortable','compact']],['imageFormat',formats],['videoFormat',['webm','mp4','gif']]])if(allowed.includes(input[key]))clean[key]=input[key]
  for(const [key,min,max] of [['fontScale',90,120],['panelWidth',280,440],['radius',0,18],['exportQuality',10,100]])if(typeof input[key]==='number'&&Number.isFinite(input[key]))clean[key]=Math.max(min,Math.min(max,Math.round(input[key])))
  if(typeof input.accent==='string'&&/^#[0-9a-f]{6}$/i.test(input.accent))clean.accent=input.accent
  if(typeof input.grid==='boolean')clean.grid=input.grid
  if(typeof input.fileName==='string')clean.fileName=input.fileName.slice(0,80)
  return clean
}
let stored={}
try{stored=JSON.parse(localStorage.getItem('AmuzASCII.ui.v1')||'null')||{};if(!stored.locale)stored.locale=navigator.language?.startsWith('ru')?'ru':'en'}catch{}
export const preferences=reactive(sanitizePreferences(stored))
export function resetAppearance(){for(const key of ['theme','accent','density','fontScale','panelWidth','radius','grid'])preferences[key]=preferenceDefaults[key]}
export function chooseTheme(id){const theme=themes.find(t=>t.id===id);if(theme){preferences.theme=theme.id;preferences.accent=theme.accent}}

watch(preferences,value=>{
  if(typeof document==='undefined')return
  const root=document.documentElement
  root.lang=value.locale;root.dataset.theme=value.theme;root.dataset.density=value.density;root.dataset.grid=String(value.grid)
  document.querySelector('meta[name="description"]')?.setAttribute('content',value.locale==='en'?'AmuzASCII — image and video ASCII art editor':'AmuzASCII — редактор ASCII-арта для изображений и видео')
  for(const [key,val] of Object.entries({'--ui-accent':value.accent,'--ui-accent-text':accentText(value.accent),'--ui-scale':value.fontScale/100,'--panel-width':value.panelWidth+'px','--ui-radius':value.radius+'px'}))root.style.setProperty(key,val)
  try{localStorage.setItem('AmuzASCII.ui.v1',JSON.stringify(value))}catch{}
},{deep:true,immediate:true})
