import test from 'node:test';
import assert from 'node:assert/strict';
import {pointerSplit,imageSplit,viewDimensions} from '../frontend/upscale-view.js';

test('dragging maps viewport coordinates to a bounded split',()=>{
  assert.equal(pointerSplit(350,100,500),50);
  assert.equal(pointerSplit(-20,100,500),0);
  assert.equal(pointerSplit(800,100,500),100);
  assert.equal(pointerSplit(10,10,0),50);
});
test('before-image clipping stays on the divider when fitted or panned',()=>{
  assert.equal(imageSplit(50,0,200,50,100),50);
  assert.equal(imageSplit(0,0,200,50,100),0);
  assert.equal(imageSplit(100,0,200,50,100),100);
  assert.equal(imageSplit(50,0,200,-100,800),25);
  assert.equal(imageSplit(50,0,200,-500,800),75);
});
test('100 and 200 percent inspect output pixels without thumbnail limits',()=>{
  assert.deepEqual(viewDimensions(2800,3400,800,500,100),{width:2800,height:3400,scale:1});
  assert.deepEqual(viewDimensions(2800,3400,800,500,200),{width:5600,height:6800,scale:2});
  const fit=viewDimensions(2800,3400,800,500,'fit');
  assert.equal(fit.height,500);
  assert.ok(fit.width<=800);
});
