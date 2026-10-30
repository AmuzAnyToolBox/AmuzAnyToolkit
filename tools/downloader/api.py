from contextlib import asynccontextmanager
import threading
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .service import DownloadStore, FORMATS

@asynccontextmanager
async def lifespan(app):
    yield
    store=getattr(app.state,'download_store',None)
    if store and not store.closed:store.shutdown()

router=APIRouter(prefix='/api/downloader',lifespan=lifespan)
lock=threading.Lock()

def store_for(request):
    with lock:
        store=getattr(request.app.state,'download_store',None)
        if store is None or store.closed:store=request.app.state.download_store=DownloadStore()
        return store

class AnalyzeInput(BaseModel):
    url:str=Field(min_length=1,max_length=4096)

class DownloadInput(BaseModel):
    quality:str=Field(default='best',pattern=r'^(best|[1-9][0-9]{0,4})$')
    format:Literal['mp4','webm','mkv','mp3','m4a']='mp4'

@router.post('/jobs',status_code=202)
def analyze(data:AnalyzeInput,request:Request):
    try:return store_for(request).analyze(data.url)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@router.get('/jobs/{key}')
def status(key:str,request:Request):
    store=store_for(request)
    return store.public(store.get(key))

@router.post('/jobs/{key}/start',status_code=202)
def start(key:str,data:DownloadInput,request:Request):
    try:return store_for(request).start(key,data.quality,data.format)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@router.delete('/jobs/{key}')
def cancel(key:str,request:Request):
    return store_for(request).cancel(key)

@router.get('/jobs/{key}/file')
def download(key:str,request:Request):
    job=store_for(request).get(key)
    if job['status']!='completed':raise HTTPException(409,'Файл ещё не готов.')
    return FileResponse(job['path'],filename=job['filename'],media_type=FORMATS[job['format']])
