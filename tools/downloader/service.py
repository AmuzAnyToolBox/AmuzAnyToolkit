"""Single-video downloads, public-address checked transport and local FFmpeg output."""
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import av
from fastapi import HTTPException
from imageio_ffmpeg import get_ffmpeg_exe
from tools.ascii.backend.remote import CheckedYoutubeDL, download_public, parse_http_url, youtube_url

MAX_BYTES = 2 * 1024**3
FORMATS = {'mp4':'video/mp4','webm':'video/webm','mkv':'video/x-matroska','mp3':'audio/mpeg','m4a':'audio/mp4'}
ACTIVE = {'analyzing','queued','downloading','converting'}

def canonical_url(url):
    parts, _ = parse_http_url(url.strip())
    if parts.scheme != 'https':
        raise ValueError('Используйте ссылку HTTPS на YouTube или Instagram.')
    host = (parts.hostname or '').lower()
    if host in {'youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be','www.youtu.be'}:
        return youtube_url(url.strip()), 'YouTube'
    if host in {'instagram.com','www.instagram.com','m.instagram.com'}:
        match = re.fullmatch(r'/(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)/?', parts.path)
        if match:
            return 'https://www.instagram.com'+parts.path.rstrip('/')+'/', 'Instagram'
        raise ValueError('Вставьте ссылку на отдельное видео, публикацию или Reels Instagram.')
    raise ValueError('Поддерживаются только YouTube и Instagram.')

def direct_formats(info):
    if not info or info.get('_type') in {'playlist','multi_video'} or info.get('entries') is not None:
        raise ValueError('Нужно одно видео. Плейлисты и подборки не поддерживаются.')
    if info.get('is_live') or info.get('live_status') in {'is_live','is_upcoming'}:
        raise ValueError('Дождитесь окончания трансляции: прямой эфир не поддерживается.')
    rows = [f for f in info.get('formats',[]) if f.get('protocol') in {'http','https'} and f.get('url') and not f.get('has_drm')]
    if not rows and info.get('url') and not info.get('has_drm') and info.get('ext') in {'mp4','webm','mkv','mov'}:
        rows = [info]
    if not any(f.get('vcodec') not in {None,'none'} for f in rows):
        raise ValueError('Нет доступного видеопотока. Ролик может требовать входа или быть недоступен в вашем регионе.')
    return rows

def select_tracks(rows, quality, output):
    videos = [f for f in rows if f.get('vcodec') not in {None,'none'}]
    audio_only = [f for f in rows if f.get('acodec') not in {None,'none'} and f.get('vcodec') == 'none']
    combined = [f for f in videos if f.get('acodec') not in {None,'none'}]
    if output in {'mp3','m4a'}:
        candidates = audio_only or combined
        if not candidates:
            raise ValueError('У видео нет доступной звуковой дорожки.')
        return [max(candidates,key=lambda f:(f.get('abr') or f.get('tbr') or 0))]
    if quality != 'best':
        videos = [f for f in videos if f.get('height') and f['height'] <= int(quality)]
    if not videos:
        raise ValueError('Выбранное разрешение недоступно. Обновите сведения о видео.')
    selected = max(videos,key=lambda f:(f.get('height') or 0,f.get('fps') or 0,f.get('tbr') or 0))
    if selected.get('acodec') not in {None,'none'}:
        return [selected]
    if audio_only:
        return [selected,max(audio_only,key=lambda f:f.get('abr') or f.get('tbr') or 0)]
    if combined:
        # A combined stream can provide audio when there is no audio-only stream.
        return [selected,max(combined,key=lambda f:f.get('abr') or f.get('tbr') or 0)]
    return [selected]

def ffmpeg_command(inputs, output, kind):
    command = [get_ffmpeg_exe(),'-nostdin','-hide_banner','-loglevel','error','-y']
    for path in inputs:
        command += ['-i',str(path)]
    with av.open(str(inputs[0])) as source:
        video = source.streams.video[0] if source.streams.video else None
        audio = source.streams.audio[0] if source.streams.audio else None
        vcodec = video.codec_context.name if video else None
        acodec = audio.codec_context.name if audio else None
    if len(inputs)>1:
        with av.open(str(inputs[1])) as source:
            acodec = source.streams.audio[0].codec_context.name if source.streams.audio else None
    audio_map = '1:a:0' if len(inputs)>1 else '0:a:0'
    if kind in {'mp3','m4a'}:
        command += ['-map','0:a:0','-vn']
        command += ['-c:a','libmp3lame','-q:a','2'] if kind=='mp3' else ['-c:a','aac','-b:a','256k']
    else:
        if not video:
            raise ValueError('В загруженном файле не обнаружена видеодорожка.')
        command += ['-map','0:v:0']
        if acodec:
            command += ['-map',audio_map]
        if kind=='mkv':
            command += ['-c','copy']
        elif kind=='mp4':
            command += ['-c:v','copy'] if vcodec=='h264' else ['-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p']
            if acodec:
                command += ['-c:a','copy'] if acodec=='aac' else ['-c:a','aac','-b:a','256k']
            command += ['-movflags','+faststart']
        elif kind=='webm':
            command += ['-c:v','copy'] if vcodec in {'vp9','vp8','av1'} else ['-c:v','libvpx-vp9','-crf','24','-b:v','0','-deadline','good','-cpu-used','3']
            if acodec:
                command += ['-c:a','copy'] if acodec in {'opus','vorbis'} else ['-c:a','libopus','-b:a','192k']
    return command+['-threads','2',str(output)]

def convert(inputs, output, kind, stop):
    command = ffmpeg_command(inputs,output,kind)
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=errors,
                                   creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        deadline = time.monotonic()+3600
        try:
            while process.poll() is None:
                if stop.wait(.2):
                    raise ValueError('Загрузка отменена.')
                if time.monotonic()>deadline:
                    raise ValueError('Превышено время подготовки файла. Попробуйте меньшее разрешение.')
                if output.exists() and output.stat().st_size>MAX_BYTES:
                    raise ValueError('Готовый файл превышает лимит 2 ГБ. Выберите меньшее разрешение.')
            if process.returncode:
                raise ValueError('Не удалось подготовить выбранный формат. Попробуйте MKV или другое разрешение.')
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
    if not output.is_file() or not 0<output.stat().st_size<=MAX_BYTES:
        raise ValueError('Готовый файл пуст или превышает 2 ГБ.')
    with av.open(str(output)) as check:
        if not check.streams.audio and kind in {'mp3','m4a'}:
            raise ValueError('Не удалось сохранить звуковую дорожку.')
        if not check.streams.video and kind not in {'mp3','m4a'}:
            raise ValueError('Не удалось сохранить видеодорожку.')

class DownloadStore:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='amuzfetch-',dir=os.environ.get('AMUZASCII_VIDEO_DIR') or None)
        self.root = Path(self.directory.name)
        self.lock = threading.RLock()
        self.pool = ThreadPoolExecutor(max_workers=2,thread_name_prefix='amuzfetch')
        self.jobs = {}
        self.closed = False

    def get(self,key):
        with self.lock:
            now=time.monotonic()
            for ident,job in list(self.jobs.items()):
                if job['status'] not in ACTIVE and now-job['touched']>3600:
                    shutil.rmtree(job['directory'],ignore_errors=True)
                    del self.jobs[ident]
            if key not in self.jobs:
                raise HTTPException(404,'Задание больше не доступно. Вставьте ссылку снова.')
            self.jobs[key]['touched']=now
            return self.jobs[key]

    def public(self,job):
        with self.lock:
            fields=['id','url','platform','status','phase','title','duration','qualities','has_audio','loaded','total','error','format','filename','size']
            result={key:job.get(key) for key in fields}
            elapsed=time.monotonic()-job.get('transfer_started',time.monotonic())
            speed=job['loaded']/elapsed if elapsed>.5 and job['status']=='downloading' else None
            result.update(speed_bps=round(speed) if speed else None,
                          eta_seconds=round(max(0,job['total']-job['loaded'])/speed) if speed and job['total'] else None,
                          download_url=f"/api/downloader/jobs/{job['id']}/file" if job['status']=='completed' else None)
            return result

    def analyze(self,url):
        canonical,platform=canonical_url(url)
        with self.lock:
            try:self.get('')
            except HTTPException:pass
            if len(self.jobs)>=16 or sum(j['status'] in ACTIVE for j in self.jobs.values())>=2:
                raise HTTPException(429,'Уже выполняются две задачи. Дождитесь окончания одной из них.')
            key=uuid.uuid4().hex
            directory=self.root/key
            directory.mkdir()
            job=dict(id=key,url=canonical,platform=platform,status='analyzing',phase='Получаем сведения о видео',
                     title='',duration=None,qualities=[],has_audio=False,loaded=0,total=None,error='',format=None,
                     filename=None,size=None,directory=directory,stop=threading.Event(),touched=time.monotonic())
            self.jobs[key]=job
            self.pool.submit(self.inspect,job)
            return self.public(job)

    def inspect(self,job):
        try:
            options=dict(quiet=True,no_warnings=True,noplaylist=True,cachedir=False,socket_timeout=15,retries=1,
                         extractor_retries=1,skip_download=True,js_runtimes={'node':{}},playlistend=1)
            with CheckedYoutubeDL(options) as client:
                info=client.extract_info(job['url'],download=False)
            rows=direct_formats(info)
            if job['stop'].is_set():raise ValueError('Загрузка отменена.')
            with self.lock:
                job.update(status='ready',phase='Выберите формат и качество',title=str(info.get('title') or job['platform'])[:200],
                           duration=info.get('duration'),qualities=sorted({int(f['height']) for f in rows if f.get('height') and f.get('vcodec') not in {None,'none'}},reverse=True),
                           has_audio=any(f.get('acodec') not in {None,'none'} for f in rows),rows=rows,touched=time.monotonic())
        except Exception as exc:self.fail(job,exc)

    def start(self,key,quality,kind):
        with self.lock:
            job=self.get(key)
            if job['status']!='ready':raise HTTPException(409,'Сначала получите сведения о новом видео.')
            if sum(j['status'] in ACTIVE for j in self.jobs.values())>=2:raise HTTPException(429,'Дождитесь окончания текущих задач.')
            tracks=select_tracks(job['rows'],quality,kind)
            if sum(f.get('filesize') or 0 for f in tracks)>MAX_BYTES:raise HTTPException(413,'Видео превышает лимит 2 ГБ. Выберите меньшее разрешение.')
            job.update(status='queued',phase='Ожидаем загрузку',format=kind)
            self.pool.submit(self.run,job,tracks)
            return self.public(job)

    def run(self,job,tracks):
        try:
            with self.lock:job.update(status='downloading',phase='Скачиваем дорожки',transfer_started=time.monotonic())
            known=[f.get('filesize') or 0 for f in tracks]
            paths=[]
            loaded=0
            for index,track in enumerate(tracks):
                base=loaded
                path=job['directory']/f'track-{index}.media'
                def report(count,length,index=index,base=base):
                    with self.lock:
                        if length:known[index]=length
                        job.update(loaded=base+count,total=sum(known) if all(known) else None,touched=time.monotonic())
                headers={k:v for k,v in track.get('http_headers',{}).items() if k.lower() in {'user-agent','referer','origin'} and isinstance(v,str) and '\n' not in v and '\r' not in v}
                download_public(track['url'],path,job['stop'],report,budget=MAX_BYTES-loaded,
                                deadline=time.monotonic()+1800,headers=headers,limit_message='Лимит загрузки — 2 ГБ. Выберите меньшее разрешение.')
                loaded+=path.stat().st_size
                known[index]=path.stat().st_size
                paths.append(path)
            if job['stop'].is_set():raise ValueError('Загрузка отменена.')
            with self.lock:job.update(status='converting',phase='Объединяем дорожки и готовим формат',loaded=loaded,total=loaded)
            temporary=job['directory']/('preparing.'+job['format'])
            convert(paths,temporary,job['format'],job['stop'])
            if job['stop'].is_set():raise ValueError('Загрузка отменена.')
            final=job['directory']/('video.'+job['format'])
            name=re.sub(r'[\x00-\x1f<>:"/\\|?*]','_',job['title']).strip('. ')[:120] or 'AmuzFetch'
            if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
                name='AmuzFetch_'+name
            with self.lock:
                if job['stop'].is_set():raise ValueError('Загрузка отменена.')
                temporary.replace(final)
                job.update(status='completed',phase='Файл готов',path=final,size=final.stat().st_size,filename=name+'.'+job['format'],touched=time.monotonic())
            for path in paths:path.unlink(missing_ok=True)
        except Exception as exc:self.fail(job,exc)

    def fail(self,job,exc):
        message=str(exc) if isinstance(exc,ValueError) else 'Сервис не выдал видео. Проверьте доступность ссылки, подключение/VPN и обновите yt-dlp. Instagram может требовать входа; закрытые публикации не поддерживаются.'
        shutil.rmtree(job['directory'],ignore_errors=True)
        with self.lock:job.update(status='cancelled' if job['stop'].is_set() else 'failed',phase='Отменено' if job['stop'].is_set() else 'Ошибка',error=message[:500],touched=time.monotonic())

    def cancel(self,key):
        with self.lock:
            job=self.get(key)
            if job['status'] in ACTIVE or job['status']=='ready':
                job['stop'].set()
                if job['status']=='ready':job.update(status='cancelled',phase='Отменено')
            return self.public(job)

    def shutdown(self):
        with self.lock:
            for job in self.jobs.values():job['stop'].set()
        self.pool.shutdown(wait=True,cancel_futures=True)
        self.directory.cleanup()
        self.closed=True
