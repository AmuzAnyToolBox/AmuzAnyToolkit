import {pointerSplit,imageSplit,viewDimensions} from './upscale-view.js';
const bytes=n=>n==null?'—':n>=1024**2?(n/1024**2).toFixed(1)+' МБ':Math.round(n/1024)+' КБ';
const active=job=>job&&['queued','processing'].includes(job.status);
const remember=id=>{try{id?localStorage.setItem('amuz.upscale.active',id):localStorage.removeItem('amuz.upscale.active');}catch{}};

export function mountUpscaler(app) {
  let file=null,job=null,localUrl=null,timer=null,disposed=false,requesting=false,selection=0;
  const controller=new AbortController();
  app.innerHTML=`<a class="breadcrumb" href="#">← Вся коллекция</a><section class="upscale-heading"><div><div class="eyebrow">AMUZUPSCALE / БОЛЬШЕ ДЕТАЛЕЙ</div><h1>Дай фото<br><em>новый масштаб.</em></h1><p>Нейросетевое увеличение ×2 и ×4. Локально, без облачного API.</p></div><div class="upscale-symbol" aria-hidden="true"><span>↗</span><small>2× / 4×</small></div></section>
    <div class="upscale-layout"><section class="panel upscale-stage-panel"><div class="upscale-stage-head"><h2 id="upscale-stage-title">Ваше фото</h2><span id="upscale-dimensions" class="small">JPEG · PNG · WebP</span></div>
      <div class="upscale-drop" id="upscale-drop"><div class="upscale-empty" id="upscale-empty"><span aria-hidden="true">↥</span><h3>Начните с фотографии</h3><p>Перетащите файл сюда или выберите на компьютере.</p><button type="button" class="primary" id="upscale-choose">Выбрать фото</button><button type="button" id="upscale-demo">Попробовать демо</button><small>До 20 МБ и 12 Мп. Результат — до 64 Мп.</small></div>
      <div class="upscale-viewer" id="upscale-viewer" hidden><div class="upscale-viewport" id="upscale-viewport" tabindex="0" aria-label="Просмотр фото: прокрутка или перетаскивание на увеличении"><div class="upscale-canvas" id="upscale-canvas"><div class="upscale-comparison" id="upscale-comparison" hidden><img id="upscale-after" alt="Увеличенное изображение" draggable="false" hidden><div id="upscale-before-layer"><img id="upscale-before" alt="Исходное изображение" draggable="false"></div></div></div></div><div class="upscale-divider" id="upscale-divider" hidden><button type="button" id="upscale-handle" role="slider" aria-label="Граница сравнения фото" aria-orientation="horizontal" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50">↔</button></div></div></div>
      <div class="upscale-view-tools" id="upscale-view-tools" hidden role="group" aria-label="Масштаб просмотра фото"><button type="button" data-view-zoom="fit" aria-pressed="true">Вписать</button><button type="button" data-view-zoom="100" aria-pressed="false">100%</button><button type="button" data-view-zoom="200" aria-pressed="false">200%</button><span id="upscale-zoom-status" class="small" role="status"></span></div><div class="upscale-toggle" id="upscale-toggle" hidden role="group" aria-label="Показать фото целиком"><button type="button" data-photo="split" aria-pressed="true">Сравнить</button><button type="button" data-photo="before" aria-pressed="false">До</button><button type="button" data-photo="after" aria-pressed="false">После</button><span class="small">Переключайте целое фото. На 100%/200% перетаскивайте его для просмотра деталей.</span></div>
      <div class="upscale-filebar" id="upscale-filebar" hidden><span id="upscale-name"></span><button type="button" id="upscale-replace">Заменить фото</button></div>
      <input type="file" id="upscale-file" accept="image/jpeg,image/png,image/webp" hidden>
      <div class="upscale-error" id="upscale-error" role="alert" hidden></div>
      <section class="upscale-progress" id="upscale-progress" hidden><div><strong id="upscale-phase" role="status"></strong><span id="upscale-percent"></span></div><progress id="upscale-bar" max="100" aria-label="Прогресс обработки"></progress><div><span id="upscale-elapsed" class="small"></span><button type="button" id="upscale-cancel">Отменить</button></div></section>
      <section class="upscale-result" id="upscale-result" hidden><div><strong>✓ Фото готово</strong><span class="small" id="upscale-result-info"></span></div><a id="upscale-download" download>↓ Скачать результат</a></section>
    </section><aside class="panel upscale-settings"><div class="eyebrow">НАСТРОЙКИ ОБРАБОТКИ</div><h2>Увеличить и уточнить.</h2>
      <form id="upscale-form"><fieldset class="upscale-scale"><legend>Увеличение</legend><label><input type="radio" name="upscale-scale" value="2" checked><span>2×<small>Вдвое по каждой стороне</small></span></label><label><input type="radio" name="upscale-scale" value="4"><span>4×<small>Для небольших исходников</small></span></label></fieldset>
      <label class="upscale-field">Метод<select id="upscale-method"><option value="ai">Нейросеть · FSRCNN</option><option value="lanczos">Быстро · Lanczos</option></select></label><p class="small" id="upscale-method-note">Нейросеть восстанавливает мелкие контуры; результат зависит от исходного фото.</p>
      <label class="upscale-check"><input type="checkbox" id="upscale-denoise">Снизить мелкий шум</label>
      <label class="upscale-range" for="upscale-sharpness">Чёткость контуров <output id="upscale-sharpness-value">55%</output><input type="range" id="upscale-sharpness" min="0" max="100" value="55"></label>
      <label class="upscale-field">Формат результата<select id="upscale-format"><option value="png">PNG · без потерь</option><option value="jpeg">JPEG · качество 95%</option><option value="webp">WebP · качество 95%</option></select></label><p id="upscale-format-note" class="small">PNG сохраняет прозрачность и все пиксели результата.</p>
      <div class="upscale-estimate" id="upscale-estimate">Выберите фото для расчёта размера.</div><button type="submit" class="primary upscale-submit" id="upscale-submit" disabled>↗ Улучшить фото</button></form>
      <details><summary>Что изменится на фото?</summary><p class="small">×2 увеличивает количество пикселей в 4 раза, ×4 — в 16. Нейросеть может сделать контуры чётче, но не возвращает достоверно утраченные детали. Lanczos плавно увеличивает изображение без нейросети. Сильная резкость может создавать ореолы.</p><p class="small">Прозрачность сохраняется в PNG/WebP; в JPEG она заменяется белым фоном. Ориентация EXIF учитывается, EXIF/GPS в результат не копируются. Обработка идёт на вашем сервере; фото не отправляется внешним AI-сервисам.</p></details><p class="upscale-retention small">Скачайте готовый файл: результаты временные, доступны до часа бездействия или до остановки сервера.</p>
    </aside></div>`;
  const find=s=>app.querySelector(s);
  const show=(s,value)=>{find(s).hidden=!value;};
  const error=message=>{find('#upscale-error').textContent=message;show('#upscale-error',!!message);};
  const scale=()=>+find('input[name="upscale-scale"]:checked').value;
  let sourceWidth=0,sourceHeight=0;

  async function api(path,options={}) {
    const response=await fetch('/api/upscaler'+path,{...options,signal:controller.signal});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Не удалось выполнить обработку. Проверьте файл и настройки.');
    return data;
  }
  function controls() {
    const processing=active(job)||requesting;
    for(const el of find('#upscale-form').elements)el.disabled=processing;
    find('#upscale-file').disabled=processing;
    find('#upscale-replace').disabled=processing;
    find('#upscale-choose').disabled=processing;
    find('#upscale-demo').disabled=processing;
    find('#upscale-cancel').disabled=!active(job);
    const tooLarge=sourceWidth*sourceHeight*scale()*scale()>64_000_000;
    find('#upscale-submit').disabled=processing||!file||tooLarge;
    find('#upscale-estimate').textContent=sourceWidth?`${sourceWidth} × ${sourceHeight} → ${sourceWidth*scale()} × ${sourceHeight*scale()} · ${(sourceWidth*sourceHeight*scale()*scale()/1e6).toFixed(1)} Мп${tooLarge?' · превышает 64 Мп':''}`:'Выберите фото для расчёта размера.';
    find('#upscale-estimate').classList.toggle('over-limit',tooLarge);
    find('#upscale-sharpness-value').textContent=find('#upscale-sharpness').value+'%';
    find('#upscale-method-note').textContent=find('#upscale-method').value==='ai'?'Нейросеть восстанавливает мелкие контуры; результат зависит от исходного фото.':'Lanczos работает быстрее: плавное увеличение без восстановления деталей нейросетью.';
    find('#upscale-format-note').textContent=({png:'PNG сохраняет прозрачность и все пиксели результата.',jpeg:'JPEG уменьшает размер файла. Прозрачный фон станет белым.',webp:'WebP сохраняет прозрачность и даёт компактный файл.'})[find('#upscale-format').value];
  }
  const viewer=find('#upscale-viewer'),viewport=find('#upscale-viewport'),canvas=find('#upscale-canvas'),plane=find('#upscale-comparison');
  let photo='split',split=50,dividerPointer=null,zoom='fit',fullReady=false,zoomTicket=0,pan=null;
  function compare(value=split) {
    split=Math.max(0,Math.min(100,Number(value)||0));
    const done=job?.status==='completed';
    const before=!done||photo!=='after';
    find('#upscale-before-layer').hidden=!before;
    const vr=viewport.getBoundingClientRect(),ir=plane.getBoundingClientRect(),frame=viewer.getBoundingClientRect();
    const left=vr.left+viewport.clientLeft,width=viewport.clientWidth;
    const clipped=imageSplit(split,left,width,ir.left,ir.width);
    find('#upscale-before-layer').style.clipPath=done&&photo==='split'?`inset(0 ${100-clipped}% 0 0)`:'none';
    find('#upscale-divider').hidden=!done||photo!=='split';
    find('#upscale-divider').style.left=(left-frame.left+width*split/100)+'px';
    find('#upscale-divider').style.height=viewport.clientHeight+'px';
    find('#upscale-handle').setAttribute('aria-valuenow',String(Math.round(split)));
    for(const button of app.querySelectorAll('[data-photo]'))button.setAttribute('aria-pressed',String(button.dataset.photo===photo));
  }
  for(const button of app.querySelectorAll('[data-photo]'))button.onclick=()=>{photo=button.dataset.photo;compare();};
  function layoutView(preserve=true) {
    if(disposed||!sourceWidth||viewer.hidden)return;
    const oldW=plane.offsetWidth,oldH=plane.offsetHeight;
    const cx=preserve&&oldW?(viewport.scrollLeft+viewport.clientWidth/2-plane.offsetLeft)/oldW:.5;
    const cy=preserve&&oldH?(viewport.scrollTop+viewport.clientHeight/2-plane.offsetTop)/oldH:.5;
    const width=job?.status==='completed'?job.output_width:sourceWidth,height=job?.status==='completed'?job.output_height:sourceHeight;
    const size=viewDimensions(width,height,viewport.clientWidth,viewport.clientHeight,zoom);
    plane.style.width=size.width+'px';plane.style.height=size.height+'px';
    canvas.style.width=Math.max(viewport.clientWidth,size.width)+'px';canvas.style.height=Math.max(viewport.clientHeight,size.height)+'px';
    viewport.scrollLeft=plane.offsetLeft+cx*size.width-viewport.clientWidth/2;
    viewport.scrollTop=plane.offsetTop+cy*size.height-viewport.clientHeight/2;
    viewer.classList.toggle('is-zoomed',zoom!=='fit');viewer.classList.toggle('is-pixel-zoom',zoom===200);
    for(const button of app.querySelectorAll('[data-view-zoom]'))button.setAttribute('aria-pressed',String(button.dataset.viewZoom===String(zoom)));
    find('#upscale-zoom-status').textContent=zoom==='fit'?`Вписано · ${Math.round(size.scale*100)}%`:`${zoom}% · ${job?.status==='completed'?'полный результат':'исходник'}`;
    compare();
  }
  function resetView() {
    zoomTicket++;zoom='fit';fullReady=false;viewport.scrollLeft=0;viewport.scrollTop=0;
    requestAnimationFrame(()=>{if(!disposed)layoutView(false);});
  }
  async function setZoom(next) {
    const ticket=++zoomTicket;
    if(next!=='fit'&&job?.status==='completed'&&!fullReady) {
      if(!job.full_before_url||!job.full_after_url){error('Перезапустите сервер и обработайте фото заново для полноразмерного просмотра.');return;}
      const snapshot=job;
      find('#upscale-zoom-status').textContent='Загружаем полный размер…';
      const before=new Image(),after=new Image();before.src=snapshot.full_before_url;after.src=snapshot.full_after_url;
      try{await Promise.all([before.decode(),after.decode()]);}
      catch{if(!disposed&&ticket===zoomTicket){error('Не удалось загрузить полный размер. Попробуйте обработать фото заново.');layoutView();}return;}
      if(disposed||ticket!==zoomTicket||job?.id!==snapshot.id)return;
      find('#upscale-before').src=before.src;find('#upscale-after').src=after.src;fullReady=true;
    }
    if(disposed||ticket!==zoomTicket)return;
    zoom=next;layoutView();
  }
  const divider=find('#upscale-divider');
  function dragSplit(e){const r=viewport.getBoundingClientRect();compare(pointerSplit(e.clientX,r.left+viewport.clientLeft,viewport.clientWidth));}
  divider.onpointerdown=e=>{if(e.button!==0)return;e.preventDefault();e.stopPropagation();dividerPointer=e.pointerId;divider.setPointerCapture(e.pointerId);find('#upscale-handle').focus({preventScroll:true});dragSplit(e);};
  divider.onpointermove=e=>{if(dividerPointer===e.pointerId){e.preventDefault();dragSplit(e);}};
  function endDivider(e){if(dividerPointer!==e.pointerId)return;dividerPointer=null;if(divider.hasPointerCapture(e.pointerId))divider.releasePointerCapture(e.pointerId);}
  divider.onpointerup=endDivider;divider.onpointercancel=endDivider;divider.onlostpointercapture=endDivider;
  find('#upscale-handle').onkeydown=e=>{const step=e.shiftKey?5:1;const values={ArrowLeft:split-step,ArrowDown:split-step,ArrowRight:split+step,ArrowUp:split+step,Home:0,End:100};if(e.key in values){e.preventDefault();compare(values[e.key]);}};
  viewport.onpointerdown=e=>{if(zoom==='fit'||e.pointerType!=='mouse'||e.button!==0)return;e.preventDefault();pan={id:e.pointerId,x:e.clientX,y:e.clientY,left:viewport.scrollLeft,top:viewport.scrollTop};viewport.setPointerCapture(e.pointerId);viewport.classList.add('panning');};
  viewport.onpointermove=e=>{if(pan?.id===e.pointerId){viewport.scrollLeft=pan.left+pan.x-e.clientX;viewport.scrollTop=pan.top+pan.y-e.clientY;compare();}};
  function endPan(e){if(pan?.id!==e.pointerId)return;pan=null;viewport.classList.remove('panning');if(viewport.hasPointerCapture(e.pointerId))viewport.releasePointerCapture(e.pointerId);}
  viewport.onpointerup=endPan;viewport.onpointercancel=endPan;viewport.onlostpointercapture=endPan;viewport.onscroll=()=>compare();
  const observer=new ResizeObserver(()=>layoutView());observer.observe(viewport);
  find('#upscale-before').onload=()=>layoutView();find('#upscale-after').onload=()=>layoutView();
  for(const button of app.querySelectorAll('[data-view-zoom]'))button.onclick=()=>setZoom(button.dataset.viewZoom==='fit'?'fit':+button.dataset.viewZoom);
  function clearResult() {
    resetView();
    show('#upscale-result',false);show('#upscale-toggle',false);show('#upscale-after',false);show('#upscale-divider',false);
    find('#upscale-before-layer').style.clipPath='none';find('#upscale-stage-title').textContent='Ваше фото';
    if(localUrl)find('#upscale-before').src=localUrl;
  }
  async function choose(selected) {
    if(!selected||active(job)||requesting)return;
    const choice=++selection;
    error('');
    if(selected.size>20*1024**2){error('Выберите фото не больше 20 МБ.');return;}
    if(!['image/jpeg','image/png','image/webp'].includes(selected.type)){error('Поддерживаются JPEG, PNG и WebP.');return;}
    const url=URL.createObjectURL(selected);
    const probe=new Image();
    try {
      probe.src=url;await probe.decode();
      if(disposed||choice!==selection||active(job)||requesting){URL.revokeObjectURL(url);return;}
      if(probe.naturalWidth*probe.naturalHeight>12_000_000)throw new Error('Исходное фото должно быть не больше 12 мегапикселей.');
      if(localUrl)URL.revokeObjectURL(localUrl);
      localUrl=url;file=selected;job=null;remember(null);
      sourceWidth=probe.naturalWidth;sourceHeight=probe.naturalHeight;
      clearResult();show('#upscale-empty',false);show('#upscale-comparison',true);show('#upscale-viewer',true);show('#upscale-view-tools',true);show('#upscale-filebar',true);
      find('#upscale-name').textContent=selected.name+' · '+bytes(selected.size);
      find('#upscale-dimensions').textContent=sourceWidth+' × '+sourceHeight;
      controls();
    } catch(exc){URL.revokeObjectURL(url);if(!disposed)error(exc.message||'Не удалось прочитать фото.');}
  }
  function render(data) {
    job=data;remember(job.id);
    const processing=active(job),done=job.status==='completed';
    show('#upscale-progress',processing);
    find('#upscale-phase').textContent=job.phase;
    find('#upscale-percent').textContent=job.progress+'%';
    find('#upscale-bar').value=job.progress;
    find('#upscale-elapsed').textContent='Прошло '+Math.round(job.elapsed_seconds||0)+' с';
    if(done) {
      sourceWidth=job.width;sourceHeight=job.height;
      find('#upscale-stage-title').textContent='Сравнение до / после';
      find('#upscale-dimensions').textContent=`${job.width} × ${job.height} → ${job.output_width} × ${job.output_height}`;
      find('#upscale-before').src=job.before_url;find('#upscale-after').src=job.after_url;
      show('#upscale-empty',false);show('#upscale-comparison',true);show('#upscale-after',true);show('#upscale-toggle',true);
      show('#upscale-viewer',true);show('#upscale-view-tools',true);resetView();photo='split';split=50;compare();
      find('#upscale-result-info').textContent=`${job.output_width} × ${job.output_height} · ${job.format.toUpperCase()} · ${bytes(job.size)} · ${job.method==='ai'?'FSRCNN':'Lanczos'}`;
      find('#upscale-download').href=job.download_url;find('#upscale-download').setAttribute('download',job.filename);
      show('#upscale-result',true);
      show('#upscale-filebar',true);
      find('#upscale-name').textContent=job.name;
    }
    if(job.error)error(job.error);
    controls();
    if(processing&&!disposed)timer=setTimeout(poll,600);
  }
  async function poll() {
    try{const data=await api('/jobs/'+job.id);if(!disposed)render(data);}
    catch(exc){if(!disposed){error(exc.message);show('#upscale-progress',false);job=null;controls();}}
  }
  find('#upscale-choose').onclick=()=>find('#upscale-file').click();
  find('#upscale-replace').onclick=()=>find('#upscale-file').click();
  find('#upscale-file').onchange=e=>{choose(e.target.files[0]);e.target.value='';};
  const drop=find('#upscale-drop');
  drop.ondragover=e=>{e.preventDefault();if(!active(job)&&!requesting)drop.classList.add('dragging');};
  drop.ondragleave=()=>drop.classList.remove('dragging');
  drop.ondrop=e=>{e.preventDefault();drop.classList.remove('dragging');choose(e.dataTransfer.files[0]);};
  find('#upscale-demo').onclick=async()=>{
    find('#upscale-demo').disabled=true;
    try{const response=await fetch('/api/demo',{signal:controller.signal});if(!response.ok)throw new Error('Демо недоступно.');const blob=await response.blob();if(!disposed)await choose(new File([blob],'botanical-demo.png',{type:'image/png'}));}
    catch(exc){if(!disposed)error(exc.message);}
    finally{if(!disposed)controls();}
  };
  find('#upscale-form').oninput=()=>{if(file&&!active(job)&&!requesting){clearResult();job=null;remember(null);}controls();};
  find('#upscale-form').onsubmit=async e=>{
    e.preventDefault();if(!file||active(job)||requesting)return;
    error('');clearTimeout(timer);clearResult();remember(null);job=null;requesting=true;controls();
    show('#upscale-progress',true);find('#upscale-phase').textContent='Загружаем фото';find('#upscale-percent').textContent='';find('#upscale-bar').removeAttribute('value');
    const form=new FormData();form.append('file',file);form.append('scale',scale());form.append('method',find('#upscale-method').value);form.append('format',find('#upscale-format').value);form.append('denoise',find('#upscale-denoise').checked);form.append('sharpness',find('#upscale-sharpness').value);
    try{const data=await api('/jobs',{method:'POST',body:form});requesting=false;if(!disposed)render(data);}
    catch(exc){requesting=false;if(!disposed){error(exc.message);show('#upscale-progress',false);controls();}}
  };
  find('#upscale-cancel').onclick=async()=>{if(!job)return;try{await api('/jobs/'+job.id,{method:'DELETE'});}catch(exc){if(!disposed)error(exc.message);}};
  controls();
  let last;try{last=localStorage.getItem('amuz.upscale.active');}catch{}
  if(last&&/^[a-f0-9]{32}$/.test(last)) {
    requesting=true;controls();
    api('/jobs/'+last).then(data=>{if(!disposed){requesting=false;find(`input[name="upscale-scale"][value="${data.scale}"]`).checked=true;find('#upscale-method').value=data.method;find('#upscale-format').value=data.format;render(data);}}).catch(()=>{remember(null);if(!disposed){requesting=false;controls();}});
  }
  return ()=>{disposed=true;zoomTicket++;observer.disconnect();clearTimeout(timer);controller.abort();if(localUrl)URL.revokeObjectURL(localUrl);};
}
