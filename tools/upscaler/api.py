from contextlib import asynccontextmanager
import threading
from typing import Literal
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from .service import MAX_UPLOAD, MEDIA_TYPES, UpscaleStore

@asynccontextmanager
async def lifespan(app):
    yield
    store=getattr(app.state,'upscale_store',None)
    if store and not store.closed:store.shutdown()

router=APIRouter(prefix='/api/upscaler',lifespan=lifespan)
lock=threading.Lock()

def store_for(request):
    with lock:
        store=getattr(request.app.state,'upscale_store',None)
        if store is None or store.closed:store=request.app.state.upscale_store=UpscaleStore()
        return store

@router.post('/jobs',status_code=202)
def start(request:Request,file:UploadFile=File(...),scale:int=Form(2,ge=2,le=4),method:Literal['ai','lanczos']=Form('ai'),
          format:Literal['png','jpeg','webp']=Form('png'),denoise:bool=Form(False),sharpness:int=Form(55,ge=0,le=100)):
    data=file.file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD:raise HTTPException(413,'Размер фото не должен превышать 20 МБ.')
    try:return store_for(request).start(data,file.filename,scale,method,format,denoise,sharpness)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@router.get('/jobs/{key}')
def status(key:str,request:Request):
    store=store_for(request)
    return store.public(store.get(key))

@router.delete('/jobs/{key}')
def cancel(key:str,request:Request):
    return store_for(request).cancel(key)

@router.get('/jobs/{key}/file')
def download(key:str,request:Request):
    job=store_for(request).get(key)
    if job['status']!='completed':raise HTTPException(409,'Результат ещё не готов.')
    return FileResponse(job['path'],filename=job['filename'],media_type=MEDIA_TYPES[job['format']])

@router.get('/jobs/{key}/{kind}')
def preview(key:str,kind:Literal['before','after'],request:Request,full:bool=False):
    job=store_for(request).get(key)
    if job['status']!='completed':raise HTTPException(409,'Результат ещё не готов.')
    if full:
        path=job['directory']/'before-full.png' if kind=='before' else job['path']
        if not path.exists():raise HTTPException(409,'Обработайте фото заново для просмотра полного разрешения.')
        return FileResponse(path,media_type='image/png' if kind=='before' else MEDIA_TYPES[job['format']])
    return FileResponse(job['directory']/(kind+'.png'),media_type='image/png')
