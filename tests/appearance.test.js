import test from 'node:test';
import assert from 'node:assert/strict';
import {sanitizeAppearance,appearanceDefaults} from '../ui-kit/appearance-state.js';

test('old theme preferences migrate without losing the selected palette',()=>{
  assert.equal(sanitizeAppearance({},'dark').theme,'graphite');
  assert.equal(sanitizeAppearance({},'ocean').accent,'#51c7b5');
  assert.deepEqual(sanitizeAppearance(null,'invalid'),appearanceDefaults);
});
test('corrupt stored appearance cannot inject CSS or break layout dimensions',()=>{
  const value=sanitizeAppearance({theme:'unknown',accent:'url(x)',fontScale:NaN,radius:-30,panelWidth:9999,density:'invalid'});
  assert.equal(value.accent,appearanceDefaults.accent);
  assert.equal(value.fontScale,100);
  assert.equal(value.radius,0);
  assert.equal(value.panelWidth,400);
  assert.equal(value.density,'comfortable');
});
test('custom appearance survives a reload while unrelated exercise settings stay out',()=>{
  const value=sanitizeAppearance({theme:'midnight',accent:'#abcdef',fontScale:115,radius:4,density:'compact',panelWidth:320,wpm:35});
  assert.deepEqual(sanitizeAppearance(JSON.parse(JSON.stringify(value))),value);
  assert.equal(value.accent,'#abcdef');
  assert.equal('wpm' in value,false);
});
