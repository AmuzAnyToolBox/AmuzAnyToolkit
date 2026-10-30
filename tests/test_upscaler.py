import io
import threading
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from server import app
from tools.upscaler import service

def photo(mode='RGB',size=(37,29)):
    y,x=np.indices((size[1],size[0]))
    rgb=np.stack([(x*11+y*3)%256,(x*5+y*13)%256,(x*17+y*7)%256],axis=2).astype(np.uint8)
    image=Image.fromarray(rgb)
    if mode=='RGBA':
        image.putalpha(Image.fromarray(((x*9+y*5)%256).astype(np.uint8)))
    return image

def upload_bytes(image,kind='PNG',**kwargs):
    stream=io.BytesIO();image.save(stream,format=kind,**kwargs);return stream.getvalue()

def wait(client,key,states={'completed','failed','cancelled'}):
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        data=client.get('/api/upscaler/jobs/'+key).json()
        if data['status'] in states:return data
        time.sleep(.02)
    raise AssertionError(data)

@pytest.mark.parametrize('scale',[2,4])
@pytest.mark.parametrize('kind',['png','jpeg','webp'])
def test_neural_workflow_produces_expected_dimensions_and_format(scale,kind):
    with TestClient(app) as client:
        image=photo('RGBA')
        response=client.post('/api/upscaler/jobs',data={'scale':scale,'format':kind,'method':'ai','sharpness':0},files={'file':('input.png',upload_bytes(image),'image/png')})
        assert response.status_code==202,response.text
        data=wait(client,response.json()['id'])
        assert data['status']=='completed',data
        assert data['progress']==100 and data['output_width']==37*scale and data['output_height']==29*scale
        assert 'directory' not in data and 'path' not in data
        response=client.get(data['download_url'])
        assert response.status_code==200
        with Image.open(io.BytesIO(response.content)) as result:
            assert result.size==(37*scale,29*scale)
            assert result.format==kind.upper()
            assert result.info.get('icc_profile')
            assert not result.getexif()
            if kind=='png':
                assert result.mode=='RGBA'
                np.testing.assert_array_equal(np.asarray(result.getchannel('A')),np.asarray(image.getchannel('A').resize(result.size,Image.Resampling.LANCZOS)))
            if kind=='jpeg':assert result.mode=='RGB'
            if kind=='webp':assert result.mode=='RGBA'
        for url in [data['before_url'],data['after_url']]:
            assert client.get(url).headers['content-type'].startswith('image/')
        for url,expected in [(data['full_before_url'],(37,29)),(data['full_after_url'],(37*scale,29*scale))]:
            with Image.open(io.BytesIO(client.get(url).content)) as full:
                assert full.size==expected

def test_lanczos_is_exact_with_filters_disabled():
    image=photo()
    result=service.enhance(image,2,'lanczos',False,0,threading.Event(),lambda *args:None)
    np.testing.assert_array_equal(np.asarray(result),np.asarray(image.resize((74,58),Image.Resampling.LANCZOS)))

def test_ai_is_not_just_lanczos_and_keeps_rgb_channel_order():
    image=photo()
    result=service.enhance(image,2,'ai',False,0,threading.Event(),lambda *args:None)
    assert not np.array_equal(np.asarray(result),np.asarray(image.resize(result.size,Image.Resampling.LANCZOS)))
    solid=service.enhance(Image.new('RGB',(20,20),(180,60,10)),2,'ai',False,0,threading.Event(),lambda *args:None)
    np.testing.assert_allclose(solid.getpixel((20,20)),(180,60,10),atol=3)

def test_overlapping_tiles_do_not_add_visible_seams():
    image=photo(size=(91,83))
    one=service.enhance(image,2,'ai',False,0,threading.Event(),lambda *args:None,tile=128)
    tiled=service.enhance(image,2,'ai',False,0,threading.Event(),lambda *args:None,tile=32)
    delta=np.abs(np.asarray(one).astype(int)-np.asarray(tiled).astype(int))
    assert delta.max()<=2,delta.max()

def test_exif_orientation_is_applied_before_dimensions():
    image=Image.new('RGB',(30,20),'red')
    exif=Image.Exif();exif[274]=6
    result=service.open_image(upload_bytes(image,'JPEG',exif=exif),2)
    assert result.size==(20,30)

@pytest.mark.parametrize('payload',[b'not an image',upload_bytes(Image.new('RGB',(10,10)),'GIF')])
def test_invalid_or_unsupported_uploads_are_rejected(payload):
    with TestClient(app) as client:
        assert client.post('/api/upscaler/jobs',files={'file':('input.png',payload,'image/png')}).status_code==400

def test_limits_are_checked_before_neural_processing(monkeypatch):
    data=upload_bytes(photo())
    monkeypatch.setattr(service,'MAX_OUTPUT_PIXELS',100)
    with pytest.raises(ValueError,match='64'):
        service.open_image(data,4)
    monkeypatch.setattr(service,'MAX_UPLOAD',2)
    with pytest.raises(ValueError,match='20'):
        service.open_image(data,2)

def test_cancelled_job_does_not_expose_partial_files(monkeypatch):
    started=threading.Event()
    def processing(image,scale,method,denoise,sharpness,stop,report):
        started.set();assert stop.wait(5);service.check_stop(stop)
    monkeypatch.setattr(service,'enhance',processing)
    with TestClient(app) as client:
        data=client.post('/api/upscaler/jobs',files={'file':('photo.png',upload_bytes(photo()),'image/png')}).json()
        key=data['id'];assert started.wait(5)
        assert client.get(f'/api/upscaler/jobs/{key}/file').status_code==409
        client.delete(f'/api/upscaler/jobs/{key}')
        assert wait(client,key)['status']=='cancelled'
        assert client.get(f'/api/upscaler/jobs/{key}/file').status_code==409
        assert client.get(f'/api/upscaler/jobs/{key}/after').status_code==409

def test_denoise_and_sharpen_are_effective():
    image=photo()
    plain=service.enhance(image,2,'lanczos',False,0,threading.Event(),lambda *args:None)
    filtered=service.enhance(image,2,'lanczos',True,50,threading.Event(),lambda *args:None)
    assert not np.array_equal(np.asarray(plain),np.asarray(filtered))

def test_full_comparison_keeps_pixels_beyond_thumbnail_limit():
    with TestClient(app) as client:
        source=Image.new('RGB',(800,500),'#a1723b')
        response=client.post('/api/upscaler/jobs',data={'scale':2,'method':'lanczos','sharpness':0},files={'file':('photo.png',upload_bytes(source),'image/png')})
        job=wait(client,response.json()['id'])
        assert job['status']=='completed',job
        with Image.open(io.BytesIO(client.get(job['after_url']).content)) as thumb:
            assert max(thumb.size)==1400
        with Image.open(io.BytesIO(client.get(job['full_after_url']).content)) as full:
            assert full.size==(1600,1000)
        with Image.open(io.BytesIO(client.get(job['full_before_url']).content)) as before:
            assert before.size==(800,500)
