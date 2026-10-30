import io
import math
import os
import shutil
import tempfile
import threading
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from fastapi import HTTPException
from PIL import Image, ImageCms, ImageFilter, ImageOps, UnidentifiedImageError

MAX_UPLOAD = 20 * 1024**2
MAX_INPUT_PIXELS = 12_000_000
MAX_OUTPUT_PIXELS = 64_000_000
TILE = 192
HALO = 16
MODELS = Path(__file__).resolve().parent / 'models'
MEDIA_TYPES = {'png':'image/png','jpeg':'image/jpeg','webp':'image/webp'}
ACTIVE = {'queued','processing'}
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()

def open_image(data,scale):
    if len(data)>MAX_UPLOAD:
        raise ValueError('Максимальный размер исходного фото — 20 МБ.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {'JPEG','PNG','WEBP'}:
                    raise ValueError('Поддерживаются JPEG, PNG и WebP.')
                if getattr(original,'n_frames',1)>1:
                    raise ValueError('Выберите статичную фотографию: анимация не поддерживается.')
                width,height=original.size
                if width*height>MAX_INPUT_PIXELS:
                    raise ValueError('Исходное изображение должно быть не больше 12 мегапикселей.')
                if width*height*scale*scale>MAX_OUTPUT_PIXELS:
                    raise ValueError('Результат превышает 64 мегапикселя. Выберите ×2 или уменьшите исходник.')
                image=ImageOps.exif_transpose(original)
                image.load()
                alpha=image.convert('RGBA').getchannel('A') if 'A' in image.getbands() or 'transparency' in image.info else None
                rgb=image.convert('RGB')
                if image.info.get('icc_profile'):
                    try:
                        rgb=ImageCms.profileToProfile(image,ImageCms.ImageCmsProfile(io.BytesIO(image.info['icc_profile'])),ImageCms.createProfile('sRGB'),outputMode='RGB')
                    except (ImageCms.PyCMSError,OSError,ValueError):
                        pass
                if alpha is not None:rgb.putalpha(alpha)
                return rgb
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
        raise ValueError('Не удалось прочитать фото. Файл повреждён или имеет слишком большое разрешение.') from exc

def check_stop(stop):
    if stop.is_set():raise ValueError('Обработка отменена.')

def enhance(image,scale,method,denoise,sharpness,stop,report,tile=TILE):
    check_stop(stop)
    width,height=image.size
    alpha=image.getchannel('A') if image.mode=='RGBA' else None
    rgb=image.convert('RGB')
    if denoise:
        report(2,'Снижаем мелкий шум')
        rgb=rgb.filter(ImageFilter.MedianFilter(3))
    check_stop(stop)
    if method=='lanczos':
        report(10,'Увеличиваем изображение')
        result=rgb.resize((width*scale,height*scale),Image.Resampling.LANCZOS)
    else:
        model=MODELS/f'FSRCNN_x{scale}.pb'
        if not model.is_file():raise ValueError('Не найдена модель FSRCNN. Восстановите каталог tools/upscaler/models.')
        cv2.setNumThreads(2)
        sr=cv2.dnn_superres.DnnSuperResImpl_create()
        sr.readModel(str(model))
        sr.setModel('fsrcnn',scale)
        source=np.asarray(rgb)
        result_array=np.empty((height*scale,width*scale,3),dtype=np.uint8)
        count=math.ceil(width/tile)*math.ceil(height/tile)
        done=0
        for y in range(0,height,tile):
            for x in range(0,width,tile):
                check_stop(stop)
                x1,y1=max(0,x-HALO),max(0,y-HALO)
                x2,y2=min(width,x+tile+HALO),min(height,y+tile+HALO)
                patch=cv2.cvtColor(np.ascontiguousarray(source[y1:y2,x1:x2]),cv2.COLOR_RGB2BGR)
                # FSRCNN's internal YCrCb operations need at least a few pixels.
                pad_y,pad_x=max(0,8-patch.shape[0]),max(0,8-patch.shape[1])
                if pad_x or pad_y:patch=cv2.copyMakeBorder(patch,0,pad_y,0,pad_x,cv2.BORDER_REPLICATE)
                enlarged=cv2.cvtColor(sr.upsample(patch),cv2.COLOR_BGR2RGB)
                out_w,out_h=min(tile,width-x)*scale,min(tile,height-y)*scale
                left,top=(x-x1)*scale,(y-y1)*scale
                result_array[y*scale:y*scale+out_h,x*scale:x*scale+out_w]=enlarged[top:top+out_h,left:left+out_w]
                done+=1
                report(5+round(77*done/count),'Восстанавливаем детали нейросетью')
        result=Image.fromarray(result_array)
    check_stop(stop)
    if sharpness:
        report(85,'Уточняем контуры')
        # Keep the sharpening footprint tied to source pixels at both output scales.
        result=result.filter(ImageFilter.UnsharpMask(radius=.8*scale,percent=round(sharpness*1.8),threshold=2))
    if alpha is not None:result.putalpha(alpha.resize(result.size,Image.Resampling.LANCZOS))
    check_stop(stop)
    return result

def save_result(image,path,kind):
    if kind=='jpeg' and image.mode=='RGBA':
        background=Image.new('RGB',image.size,'white')
        background.paste(image,mask=image.getchannel('A'))
        image=background
    options={'icc_profile':SRGB}
    if kind=='jpeg':options.update(quality=95,subsampling=0)
    elif kind=='webp':options.update(quality=95,method=4)
    else:options.update(compress_level=4)
    # Do not copy EXIF (including GPS), thumbnails or unrelated metadata.
    clean=Image.fromarray(np.asarray(image))
    clean.save(path,format=kind.upper(),**options)

def preview(image,path):
    image=image.copy()
    image.thumbnail((1400,1400),Image.Resampling.LANCZOS)
    Image.fromarray(np.asarray(image)).save(path,format='PNG',icc_profile=SRGB)

class UpscaleStore:
    def __init__(self):
        self.directory=tempfile.TemporaryDirectory(prefix='amuzupscale-',dir=os.environ.get('AMUZASCII_VIDEO_DIR') or None)
        self.root=Path(self.directory.name)
        self.lock=threading.RLock()
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='amuzupscale')
        self.jobs={}
        self.closed=False

    def get(self,key):
        with self.lock:
            for ident,job in list(self.jobs.items()):
                if job['status'] not in ACTIVE and time.monotonic()-job['touched']>3600:
                    shutil.rmtree(job['directory'],ignore_errors=True)
                    del self.jobs[ident]
            if key not in self.jobs:raise HTTPException(404,'Результат больше не доступен. Загрузите фото снова.')
            self.jobs[key]['touched']=time.monotonic()
            return self.jobs[key]

    def public(self,job):
        with self.lock:
            keys=['id','status','phase','progress','name','width','height','scale','method','format','error','size']
            data={key:job.get(key) for key in keys}
            data.update(output_width=job['width']*job['scale'],output_height=job['height']*job['scale'],
                        elapsed_seconds=round(time.monotonic()-job['started'],1) if job['status'] in ACTIVE else job.get('elapsed_seconds',0))
            if job['status']=='completed':
                data.update(before_url=f"/api/upscaler/jobs/{job['id']}/before",after_url=f"/api/upscaler/jobs/{job['id']}/after",
                            full_before_url=f"/api/upscaler/jobs/{job['id']}/before?full=true",full_after_url=f"/api/upscaler/jobs/{job['id']}/after?full=true",
                            download_url=f"/api/upscaler/jobs/{job['id']}/file",filename=job['filename'])
            return data

    def start(self,data,name,scale,method,kind,denoise,sharpness):
        if scale not in {2,4} or method not in {'ai','lanczos'} or kind not in MEDIA_TYPES or not 0<=sharpness<=100:
            raise ValueError('Недопустимые параметры обработки.')
        with self.lock:
            try:self.get('')
            except HTTPException:pass
            if len(self.jobs)>=12 or sum(j['status'] in ACTIVE for j in self.jobs.values())>=2:
                raise HTTPException(429,'Уже обрабатываются два фото. Дождитесь результата.')
        image=open_image(data,scale)
        width,height=image.size
        image.close()
        with self.lock:
            if sum(j['status'] in ACTIVE for j in self.jobs.values())>=2:raise HTTPException(429,'Дождитесь завершения текущей обработки.')
            key=uuid.uuid4().hex
            directory=self.root/key
            directory.mkdir()
            (directory/'source.media').write_bytes(data)
            job=dict(id=key,status='queued',phase='Ожидаем обработки',progress=0,name=str(name or 'photo')[:150],width=width,height=height,
                     scale=scale,method=method,format=kind,error='',size=None,directory=directory,stop=threading.Event(),
                     touched=time.monotonic(),started=time.monotonic())
            self.jobs[key]=job
            self.pool.submit(self.run,job,denoise,sharpness)
            return self.public(job)

    def run(self,job,denoise,sharpness):
        def report(progress,phase):
            with self.lock:job.update(status='processing',progress=progress,phase=phase,touched=time.monotonic())
        try:
            report(1,'Читаем фото')
            image=open_image((job['directory']/'source.media').read_bytes(),job['scale'])
            check_stop(job['stop'])
            preview(image,job['directory']/'before.png')
            save_result(image,job['directory']/'before-full.png','png')
            result=enhance(image,job['scale'],job['method'],denoise,sharpness,job['stop'],report)
            report(90,'Сохраняем результат')
            temporary=job['directory']/('preparing.'+job['format'])
            save_result(result,temporary,job['format'])
            preview(result,job['directory']/'after.png')
            final=job['directory']/('upscaled.'+job['format'])
            filename=f"AmuzUpscale-{job['width']*job['scale']}x{job['height']*job['scale']}.{('jpg' if job['format']=='jpeg' else job['format'])}"
            with self.lock:
                check_stop(job['stop'])
                temporary.replace(final)
                job.update(status='completed',phase='Фото готово',progress=100,path=final,size=final.stat().st_size,filename=filename,
                           elapsed_seconds=round(time.monotonic()-job['started'],1),touched=time.monotonic())
            image.close()
            result.close()
            (job['directory']/'source.media').unlink(missing_ok=True)
        except Exception as exc:
            message=str(exc) if isinstance(exc,ValueError) else 'Не удалось обработать фото. Попробуйте меньший размер или быстрый режим Lanczos.'
            shutil.rmtree(job['directory'],ignore_errors=True)
            with self.lock:job.update(status='cancelled' if job['stop'].is_set() else 'failed',phase='Отменено' if job['stop'].is_set() else 'Ошибка',error=message[:400],elapsed_seconds=round(time.monotonic()-job['started'],1),touched=time.monotonic())

    def cancel(self,key):
        with self.lock:
            job=self.get(key)
            if job['status'] in ACTIVE:job['stop'].set()
            return self.public(job)

    def shutdown(self):
        with self.lock:
            for job in self.jobs.values():job['stop'].set()
        self.pool.shutdown(wait=True,cancel_futures=True)
        self.directory.cleanup()
        self.closed=True
