import shutil
import threading
import time
from pathlib import Path

import av
import pytest
from fastapi.testclient import TestClient
from server import app
from tools.downloader import service
from tools.ascii.backend.test_video import make_video

def wait_job(client,key,states):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        data=client.get('/api/downloader/jobs/'+key).json()
        if data['status'] in states:return data
        time.sleep(.02)
    raise AssertionError(data)

@pytest.mark.parametrize('url',[
    'http://www.youtube.com/watch?v=jNQXAC9IVRw','file:///etc/passwd','https://127.0.0.1/x',
    'https://youtube.com.evil.test/watch?v=jNQXAC9IVRw','https://user:password@instagram.com/reel/a/',
    'https://youtube.com:444/watch?v=jNQXAC9IVRw','https://www.youtube.com/playlist?list=x',
    'https://www.instagram.com/some_profile/',
])
def test_only_single_public_platform_links(url):
    with pytest.raises(ValueError):service.canonical_url(url)

def test_shared_links_are_canonicalized():
    assert service.canonical_url('https://youtu.be/jNQXAC9IVRw?si=x&t=5')[0]=='https://www.youtube.com/watch?v=jNQXAC9IVRw'
    assert service.canonical_url('https://www.instagram.com/reel/ABC_12/?igsh=x')==('https://www.instagram.com/reel/ABC_12/','Instagram')

@pytest.fixture
def local_media(tmp_path,monkeypatch):
    combined=tmp_path/'source.mp4'
    make_video(combined)
    tracks={}
    for kind in ['video','audio']:
        path=tmp_path/(kind+'.mkv')
        with av.open(str(combined)) as source,av.open(str(path),'w') as output:
            stream=getattr(source.streams,kind)[0]
            target=output.add_stream_from_template(stream)
            for packet in source.demux(stream):
                if packet.size and (packet.dts is not None or packet.pts is not None):
                    packet.stream=target
                    output.mux(packet)
        tracks[kind]=path
    rows=[dict(protocol='https',url='https://cdn.example/video',vcodec='h264',acodec='none',height=720,tbr=4000),
          dict(protocol='https',url='https://cdn.example/audio',vcodec='none',acodec='aac',abr=128)]
    class FakeYoutube:
        def __init__(self,options):assert options['noplaylist'] and options['skip_download']
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,url,download=False):return dict(title='Тест: видео/2026',duration=2,formats=rows)
    monkeypatch.setattr(service,'CheckedYoutubeDL',FakeYoutube)
    def download(url,path,stop,report,**kwargs):
        if stop.is_set():raise ValueError('Загрузка отменена.')
        shutil.copyfile(tracks['video' if url.endswith('video') else 'audio'],path)
        report(path.stat().st_size,path.stat().st_size)
    monkeypatch.setattr(service,'download_public',download)
    return rows

def test_resolution_selection_and_audio_preservation(local_media):
    rows=local_media+[dict(local_media[0],height=1080,tbr=6000)]
    assert service.select_tracks(rows,'720','mp4')[0]['height']==720
    assert service.select_tracks(rows,'best','mkv')[0]['height']==1080
    assert len(service.select_tracks(rows,'best','webm'))==2
    assert service.select_tracks(rows,'best','mp3')[0]['vcodec']=='none'
    with pytest.raises(ValueError):service.select_tracks(rows,'360','mp4')

@pytest.mark.parametrize('kind',['mp4','webm','mkv','mp3','m4a'])
def test_full_workflow_produces_real_complete_media(local_media,tmp_path,kind):
    with TestClient(app) as client:
        job=client.post('/api/downloader/jobs',json={'url':'https://youtu.be/jNQXAC9IVRw'}).json()
        key=job['id']
        assert client.get(f'/api/downloader/jobs/{key}/file').status_code==409
        ready=wait_job(client,key,{'ready','failed'})
        assert ready['status']=='ready',ready
        assert ready['qualities']==[720] and ready['has_audio']
        assert 'rows' not in ready and 'directory' not in ready
        response=client.post(f'/api/downloader/jobs/{key}/start',json={'quality':'720','format':kind})
        assert response.status_code==202,response.text
        completed=wait_job(client,key,{'completed','failed'})
        assert completed['status']=='completed',completed
        response=client.get(completed['download_url'])
        assert response.status_code==200 and len(response.content)==completed['size']
        assert '/' not in completed['filename'] and ':' not in completed['filename']
        output=tmp_path/('result.'+kind)
        output.write_bytes(response.content)
        with av.open(str(output)) as media:
            assert media.streams.audio
            assert abs(media.duration/av.time_base-2)<.3
            if kind in {'mp4','webm','mkv'}:
                assert media.streams.video
                assert sum(1 for _ in media.decode(video=0))==24
            else:
                assert not media.streams.video
        assert client.post(f'/api/downloader/jobs/{key}/start',json={}).status_code==409

def test_cancelled_transfer_never_exposes_partial_media(local_media,monkeypatch):
    started=threading.Event()
    def download(url,path,stop,report,**kwargs):
        path.write_bytes(b'partial')
        started.set()
        assert stop.wait(5)
        raise ValueError('Загрузка отменена.')
    monkeypatch.setattr(service,'download_public',download)
    with TestClient(app) as client:
        key=client.post('/api/downloader/jobs',json={'url':'https://instagram.com/reel/ABC123/'}).json()['id']
        assert wait_job(client,key,{'ready','failed'})['status']=='ready'
        assert client.post(f'/api/downloader/jobs/{key}/start',json={}).status_code==202
        assert started.wait(5)
        client.delete(f'/api/downloader/jobs/{key}')
        assert wait_job(client,key,{'cancelled','failed'})['status']=='cancelled'
        assert client.get(f'/api/downloader/jobs/{key}/file').status_code==409

def test_conversion_failure_is_clean_and_reported(local_media,monkeypatch):
    def fail(*args):raise ValueError('Тест ошибки подготовки')
    monkeypatch.setattr(service,'convert',fail)
    with TestClient(app) as client:
        key=client.post('/api/downloader/jobs',json={'url':'https://youtu.be/jNQXAC9IVRw'}).json()['id']
        wait_job(client,key,{'ready','failed'})
        client.post(f'/api/downloader/jobs/{key}/start',json={})
        failed=wait_job(client,key,{'failed'})
        assert failed['error']=='Тест ошибки подготовки'
        assert not app.state.download_store.get(key)['directory'].exists()
        assert client.get(f'/api/downloader/jobs/{key}/file').status_code==409

def test_metadata_rejects_playlists_livestreams_and_drm():
    for info in [dict(_type='playlist',entries=[]),dict(is_live=True),dict(formats=[dict(url='https://x',protocol='https',has_drm=True)])]:
        with pytest.raises(ValueError):service.direct_formats(info)
