import test from 'node:test';
import assert from 'node:assert/strict';
import {alphabet,encode,decode,schedule,classify} from '../frontend/morse.js';
test('All alphabets round-trip, including Russian-only letters and digits',()=>{for(const lang of ['ru','en'])for(const x of alphabet(lang,true))assert.equal(decode(encode(x[lang],lang),lang),x[lang]);assert.equal(alphabet('en').length,26);assert.equal(alphabet('ru').length,31);});
test('Words, aliases and unsupported characters',()=>{assert.equal(encode('SOS','en'),'... --- ...');assert.equal(decode(encode('Привет мир','ru'),'ru'),'ПРИВЕТ МИР');assert.equal(decode(encode('ЁЖ Ъ','ru'),'ru'),'ЕЖ Ь');assert.equal(encode('!','en'),'?');assert.equal(decode('• — / — •','ru'),'ЕТ ТЕ');});
test('PARIS standard is 50 units including the word gap',()=>{const timing=schedule(encode('PARIS','en'),1);assert.equal(timing.duration+7,50);});
test('Signal spacing: intra-letter 1, letter 3, word 7 units',()=>{assert.deepEqual(schedule('.- . / -',1).tones,[{time:0,duration:1},{time:2,duration:3},{time:8,duration:1},{time:16,duration:3}]);assert.equal(classify(199,100),'.');assert.equal(classify(200,100),'-');});
test('Pasted multiline Morse uses the same decoding and audio spacing',()=>{
 const code='  •••\t−−−\n···/\n•   —  ';
 assert.equal(decode(code,'en'),'SOS ET');
 assert.deepEqual(schedule(code,1),schedule('... --- ... / . -',1));
 assert.equal(decode('   \n\t','ru'),'');
 assert.deepEqual(schedule(' \n ',1),{tones:[],duration:0});
});
test('Long messages retain every word and digit through conversion',()=>{
 for(const [lang,text] of [['ru','ПРИВЕТ МИР РАДИО СИГНАЛ 2026'],['en','HELLO WORLD RADIO SIGNAL 2026']])
   assert.equal(decode(encode(text,lang),lang),text);
});
