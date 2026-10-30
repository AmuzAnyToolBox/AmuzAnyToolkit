import {themes,accentText} from './themes.js';
import {appearanceDefaults,sanitizeAppearance} from './appearance-state.js';

function load(key,fallback) {try{return JSON.parse(localStorage.getItem(key)) ?? fallback;}catch{return fallback;}}
function save(key,value) {try{localStorage.setItem(key,JSON.stringify(value));}catch{}}

/** Reusable visual appearance picker for buildless tools. Settings apply live. */
export function mountAppearance(trigger,{onOpen=()=>{}}={}) {
  let state = sanitizeAppearance(load('amuz.appearance.v1',{}),load('amuz.theme','paper'));
  const dialog = document.createElement('dialog');
  dialog.className = 'amuz-appearance';
  dialog.setAttribute('aria-labelledby','appearance-title');
  dialog.innerHTML = `
    <div class="appearance-heading"><div><span class="appearance-eyebrow">AMUZ / ВАШЕ ПРОСТРАНСТВО</span><h2 id="appearance-title">Оформление</h2><p>Выберите настроение. Цвета применяются сразу.</p></div><button type="button" data-close aria-label="Закрыть оформление">×</button></div>
    <div class="appearance-body">
      <div class="appearance-section-heading"><h3>Тема интерфейса</h3><span>12 палитр</span></div>
      <div class="appearance-themes" role="group" aria-label="Темы интерфейса">
        ${themes.map(t=>`<button type="button" class="appearance-theme" data-theme-choice="${t.id}" aria-label="Тема ${t.name}" aria-pressed="false" style="--preview-bg:${t.colors[0]};--preview-panel:${t.colors[1]};--preview-ink:${t.colors[2]};--preview-accent:${t.accent}">
          <span class="appearance-preview" aria-hidden="true"><span class="preview-bar"><i></i><i></i><i></i></span><span class="preview-content"><span class="preview-sidebar"></span><span class="preview-copy"><b>Aa</b><span></span><span></span></span><span class="preview-action">↗</span></span></span>
          <span class="appearance-theme-caption"><span>${t.name}</span><span class="theme-check" aria-hidden="true">✓</span></span>
          <span class="appearance-palette" aria-hidden="true">${[...t.colors,t.accent].map(c=>`<i style="background:${c}"></i>`).join('')}</span>
        </button>`).join('')}
      </div>
      <section class="appearance-options" aria-label="Настройки интерфейса">
        <div class="appearance-section-heading"><h3>Детали интерфейса</h3><span>Под себя</span></div>
        <div class="appearance-option-grid"><label class="appearance-field">Акцентный цвет<span class="appearance-color"><input type="color" id="appearance-accent"><output id="appearance-accent-value"></output></span></label>
        <fieldset class="appearance-density"><legend>Плотность</legend><div><button type="button" data-density="comfortable" aria-pressed="false">Комфортная</button><button type="button" data-density="compact" aria-pressed="false">Компактная</button></div></fieldset></div>
        <div class="appearance-ranges">
          <label for="appearance-fontScale">Размер текста <output id="appearance-fontScale-value"></output><input id="appearance-fontScale" type="range" min="90" max="120" step="5"></label>
          <label for="appearance-radius">Скругление <output id="appearance-radius-value"></output><input id="appearance-radius" type="range" min="0" max="18"></label>
          <label for="appearance-panelWidth">Ширина панели Морзе <output id="appearance-panelWidth-value"></output><input id="appearance-panelWidth" type="range" min="240" max="400" step="10"></label>
        </div>
      </section>
      <p class="appearance-hint">Настройки сохраняются в этом браузере для хаба и Морзе. Оформление ASCII настраивается внутри студии.</p>
    </div>
    <div class="appearance-footer"><button type="button" id="appearance-reset">Сбросить оформление</button><span role="status" id="appearance-status">Сохранено в браузере</span><button type="button" class="primary" data-close>Готово</button></div>`;
  document.body.append(dialog);
  const find = s=>dialog.querySelector(s);

  function apply() {
    const root = document.documentElement;
    root.dataset.theme = state.theme;
    root.dataset.density = state.density;
    for (const [key,value] of Object.entries({'--ui-accent':state.accent,'--ui-accent-text':accentText(state.accent),'--ui-scale':state.fontScale/100,'--ui-radius':state.radius+'px','--morse-panel-width':state.panelWidth+'px'})) root.style.setProperty(key,value);
    const t = themes.find(t=>t.id===state.theme);
    trigger.innerHTML = `<span class="appearance-trigger-palette" aria-hidden="true">${[t.colors[0],t.colors[2],state.accent].map(c=>`<i style="background:${c}"></i>`).join('')}</span><span>Оформление<span class="appearance-current">${t.name}</span></span><span aria-hidden="true">⌄</span>`;
    dialog.querySelectorAll('[data-theme-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.themeChoice===state.theme)));
    dialog.querySelectorAll('[data-density]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.density===state.density)));
    find('#appearance-accent').value = state.accent;
    find('#appearance-accent-value').textContent = state.accent.toUpperCase();
    for (const key of ['fontScale','radius','panelWidth']) {
      find('#appearance-'+key).value = state[key];
      find('#appearance-'+key+'-value').textContent = state[key]+(key==='fontScale'?'%':' px');
    }
    save('amuz.appearance.v1',state);
    save('amuz.theme',state.theme);
    find('#appearance-status').textContent='Сохранено в браузере';
  }
  dialog.querySelectorAll('[data-theme-choice]').forEach(b=>b.onclick=()=>{state.theme=b.dataset.themeChoice;state.accent=themes.find(t=>t.id===state.theme).accent;apply();});
  dialog.querySelectorAll('[data-density]').forEach(b=>b.onclick=()=>{state.density=b.dataset.density;apply();});
  for (const key of ['accent','fontScale','radius','panelWidth']) find('#appearance-'+key).oninput=e=>{state[key]=key==='accent'?e.target.value:+e.target.value;apply();};
  find('#appearance-reset').onclick=()=>{state={...appearanceDefaults};apply();};
  dialog.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>dialog.close());
  dialog.onclick=e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}};
  trigger.setAttribute('aria-haspopup','dialog');
  trigger.setAttribute('aria-controls','amuz-appearance-dialog');
  dialog.id='amuz-appearance-dialog';
  trigger.onclick=()=>{onOpen();dialog.showModal();dialog.scrollTop=0;};
  apply();
  return dialog;
}
