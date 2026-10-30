const bytes = n=>n==null?'—':n>=1024**3?(n/1024**3).toFixed(2)+' ГБ':n>=1024**2?(n/1024**2).toFixed(1)+' МБ':Math.round(n/1024)+' КБ';
const duration = n=>n==null?'—':`${Math.floor(n/60)}:${String(Math.floor(n%60)).padStart(2,'0')}`;
const busy = state=>['analyzing','queued','downloading','converting'].includes(state);

export function mountDownloader(app) {
  let timer=null,disposed=false,job=null,requesting=false;
  const controller=new AbortController();
  app.innerHTML=`<a class="breadcrumb" href="#">← Вся коллекция</a><section class="fetch-heading"><div><div class="eyebrow">AMUZFETCH / СОХРАНИ МОМЕНТ</div><h1>Видео —<br><em>в твоих руках.</em></h1><p>Одна ссылка. Нужное качество. Твой формат.</p></div><div class="fetch-symbol" aria-hidden="true">↙<span>YOUTUBE + INSTAGRAM</span></div></section>
    <div class="fetch-workspace"><section class="panel fetch-main"><div class="fetch-step"><span>01</span><h2>Вставьте ссылку</h2></div>
    <form id="fetch-form" class="fetch-link"><label for="fetch-url" class="small">YouTube, Shorts, Instagram Reels или отдельное видео</label><div><input id="fetch-url" type="url" required placeholder="https://www.youtube.com/watch?v=…" autocomplete="off"><button class="primary" id="fetch-analyze">Найти видео ↗</button></div></form>
    <div id="fetch-error" class="fetch-error" role="alert" hidden></div>
    <section id="fetch-preview" class="fetch-preview" hidden><div class="fetch-source-icon" aria-hidden="true">▶</div><div><span id="fetch-platform" class="eyebrow"></span><h3 id="fetch-title"></h3><span id="fetch-duration" class="small"></span></div></section>
    <section id="fetch-options" hidden><div class="fetch-step"><span>02</span><h2>Выберите результат</h2></div><div class="fetch-fields"><label>Формат<select id="fetch-format"><optgroup label="Видео"><option value="mp4">MP4 · совместимость</option><option value="webm">WebM · для веба</option><option value="mkv">MKV · исходные дорожки</option></optgroup><optgroup label="Только аудио"><option value="mp3">MP3 · звук</option><option value="m4a">M4A · звук AAC</option></optgroup></select></label><label>Качество<select id="fetch-quality"><option value="best">Лучшее доступное</option></select></label></div><p id="fetch-format-note" class="small"></p><button id="fetch-start" class="primary fetch-start">↓ Подготовить файл</button></section>
    <section id="fetch-progress" class="fetch-progress" hidden aria-label="Ход загрузки"><div class="fetch-progress-label"><strong id="fetch-phase" role="status"></strong><span id="fetch-percent"></span></div><progress id="fetch-bar" max="100" aria-label="Прогресс загрузки"></progress><div class="fetch-transfer"><span id="fetch-loaded"></span><span id="fetch-speed"></span><span id="fetch-eta"></span></div><button id="fetch-cancel">Отменить</button></section>
    <section id="fetch-result" class="fetch-result" hidden><div><span aria-hidden="true">✓</span><div><h2>Готово к скачиванию</h2><p id="fetch-result-info" class="small"></p></div></div><a id="fetch-download" class="fetch-download" download>↓ Скачать файл</a><button id="fetch-again">Другой формат или качество</button></section>
    </section><aside class="panel fetch-guide"><div class="eyebrow">БЕЗ ЛИШНИХ ПОТЕРЬ</div><h2>Качество задаёт источник.</h2><p>Показываем разрешения, которые действительно доступны у ролика. «Лучшее» выбирает самый качественный доступный поток; разрешение не увеличивается искусственно.</p><div class="fetch-guide-row"><strong>MP4</strong><span>H.264 + AAC. Если дорожки совместимы, сохраняем их без перекодирования.</span></div><div class="fetch-guide-row"><strong>MKV</strong><span>Объединяем исходные дорожки без перекодирования. Подходит для сохранения качества.</span></div><div class="fetch-guide-row"><strong>WebM</strong><span>VP9/AV1 + Opus. Несовместимые дорожки преобразуем.</span></div><div class="fetch-guide-row"><strong>Аудио</strong><span>MP3 или M4A — только звуковая дорожка.</span></div><p class="small">До 2 ГБ на результат. Готовые файлы временные: доступны в течение часа бездействия, пока сервер работает. Скачайте результат на свой компьютер.</p><details><summary>Если сервис не отдаёт видео</summary><p class="small">Instagram может требовать входа, а YouTube — проверку доступа. Закрытые публикации, прямые эфиры, плейлисты и DRM не поддерживаются. Проверьте ссылку, VPN и обновите yt-dlp по инструкции в README.</p></details></aside></div>`;
  const find=s=>app.querySelector(s);
  const show=(s,value)=>{find(s).hidden=!value;};
  const error=message=>{find('#fetch-error').textContent=message;show('#fetch-error',!!message);};
  const remember=id=>{try{id?localStorage.setItem('amuz.fetch.active',id):localStorage.removeItem('amuz.fetch.active');}catch{}};

  async function api(path,options={}) {
    const response=await fetch('/api/downloader'+path,{...options,signal:controller.signal,headers:{'Content-Type':'application/json',...options.headers}});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Не удалось выполнить запрос. Проверьте ссылку и попробуйте снова.');
    return data;
  }
  function formatNote() {
    const kind=find('#fetch-format').value,audio=['mp3','m4a'].includes(kind);
    find('#fetch-quality').disabled=audio||job?.status!=='ready';
    const notes={mp4:'Для большинства устройств. При необходимости преобразуем в H.264/AAC с высоким качеством.',webm:'Для браузеров. Подготовка WebM может занять больше времени.',mkv:'Сохраняем исходные кодеки и качество; для просмотра подойдёт VLC.',mp3:'Только звук. MP3 VBR высокого качества; разрешение видео не используется.',m4a:'Только звук. AAC 256 кбит/с; разрешение видео не используется.'};
    find('#fetch-format-note').textContent=notes[kind];
  }
  function render(data) {
    job=data;remember(job.id);
    const active=busy(job.status),ready=job.status==='ready',completed=job.status==='completed';
    find('#fetch-url').disabled=active;
    find('#fetch-analyze').disabled=active||requesting;
    show('#fetch-preview',!!job.title);
    find('#fetch-title').textContent=job.title||'';
    find('#fetch-platform').textContent=job.platform;
    find('#fetch-duration').textContent=`${duration(job.duration)} · ${job.has_audio?'Видео со звуком':'Источник без звука'}`;
    show('#fetch-options',ready);
    if(ready) {
      find('#fetch-quality').innerHTML='<option value="best">Лучшее доступное</option>'+job.qualities.filter(n=>Number.isInteger(n)&&n>0).map(n=>`<option value="${n}">${n}p${n===2160?' · 4K':n===4320?' · 8K':''}</option>`).join('');
      for(const option of find('#fetch-format').options)option.disabled=!job.has_audio&&['mp3','m4a'].includes(option.value);
      if(!job.has_audio&&['mp3','m4a'].includes(find('#fetch-format').value))find('#fetch-format').value='mp4';
    }
    show('#fetch-progress',active);
    find('#fetch-phase').textContent=job.phase;
    const ratio=job.total?Math.min(100,Math.round(100*job.loaded/job.total)):null;
    if(job.status==='downloading'&&ratio!==null)find('#fetch-bar').value=ratio;else find('#fetch-bar').removeAttribute('value');
    find('#fetch-percent').textContent=job.status==='downloading'&&ratio!==null?ratio+'%':'';
    find('#fetch-loaded').textContent=job.status==='analyzing'?'Проверяем доступные дорожки':`${bytes(job.loaded)} / ${bytes(job.total)}`;
    find('#fetch-speed').textContent=job.speed_bps?bytes(job.speed_bps)+'/с':'';
    find('#fetch-eta').textContent=job.eta_seconds!=null?'Осталось ≈ '+duration(job.eta_seconds):'';
    show('#fetch-result',completed);
    if(completed) {
      find('#fetch-result-info').textContent=`${job.filename} · ${bytes(job.size)}`;
      find('#fetch-download').href=job.download_url;
      find('#fetch-download').setAttribute('download',job.filename);
    }
    find('#fetch-cancel').disabled=false;
    if(job.error)error(job.error);
    else if(job.status==='cancelled')error('Загрузка отменена. Можно вставить ссылку снова.');
    formatNote();
    if(active&&!disposed)timer=setTimeout(poll,1000);
  }
  async function poll() {
    try{const data=await api('/jobs/'+job.id);if(!disposed)render(data);}
    catch(exc){if(!disposed){error(exc.message);show('#fetch-progress',false);find('#fetch-url').disabled=false;find('#fetch-analyze').disabled=false;}}
  }
  async function analyze() {
    if(requesting||busy(job?.status))return;
    error('');job=null;remember(null);show('#fetch-result',false);show('#fetch-options',false);show('#fetch-preview',false);requesting=true;find('#fetch-analyze').disabled=true;
    clearTimeout(timer);
    try{const data=await api('/jobs',{method:'POST',body:JSON.stringify({url:find('#fetch-url').value.trim()})});requesting=false;if(!disposed)render(data);}
    catch(exc){if(!disposed)error(exc.message);}
    finally{requesting=false;if(!disposed)find('#fetch-analyze').disabled=busy(job?.status);}
  }
  find('#fetch-form').onsubmit=e=>{e.preventDefault();analyze();};
  find('#fetch-format').onchange=formatNote;
  find('#fetch-start').onclick=async()=>{
    if(job?.status!=='ready'||requesting)return;
    error('');requesting=true;find('#fetch-start').disabled=true;
    try{const data=await api('/jobs/'+job.id+'/start',{method:'POST',body:JSON.stringify({format:find('#fetch-format').value,quality:find('#fetch-quality').value})});if(!disposed)render(data);}
    catch(exc){if(!disposed)error(exc.message);}
    finally{requesting=false;if(!disposed)find('#fetch-start').disabled=false;}
  };
  find('#fetch-cancel').onclick=async()=>{find('#fetch-cancel').disabled=true;try{await api('/jobs/'+job.id,{method:'DELETE'});}catch(exc){if(!disposed)error(exc.message);}};
  find('#fetch-again').onclick=()=>{job=null;remember(null);show('#fetch-result',false);show('#fetch-preview',false);find('#fetch-url').focus();analyze();};
  formatNote();
  const last=(()=>{try{return localStorage.getItem('amuz.fetch.active');}catch{return null;}})();
  if(last&&/^[a-f0-9]{32}$/.test(last)) {
    find('#fetch-analyze').disabled=true;find('#fetch-url').disabled=true;
    requesting=true;
    api('/jobs/'+last).then(data=>{if(!disposed){requesting=false;find('#fetch-url').value=data.url;render(data);}}).catch(()=>{remember(null);requesting=false;if(!disposed){find('#fetch-analyze').disabled=false;find('#fetch-url').disabled=false;}});
  }
  return ()=>{disposed=true;clearTimeout(timer);controller.abort();};
}
