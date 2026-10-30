const rows = [
 ['А','A','.-','ай-да'],['Б','B','-...','ба-ки-те-кут'],['В','W','.--','ви-да-ла'],['Г','G','--.','га-ра-жи'],['Д','D','-..','до-ми-ки'],['Е','E','.','есть'],['Ж','V','...-','же-ле-зи-сто'],['З','Z','--..','за-ка-ти-ки'],['И','I','..','и-ди'],['Й','J','.---','и-крат-ко-е'],['К','K','-.-','как-де-ла'],['Л','L','.-..','лу-на-ти-ки'],['М','M','--','ма-ма'],['Н','N','-.','но-мер'],['О','O','---','о-ко-ло'],['П','P','.--.','пи-ла-по-ёт'],['Р','R','.-.','ре-ша-ет'],['С','S','...','си-не-е'],['Т','T','-','так'],['У','U','..-','у-нес-ло'],['Ф','F','..-.','фи-ли-мон-чик'],['Х','H','....','хи-ми-чи-те'],['Ц','C','-.-.','цап-ли-на-ши'],['Ч','','---.','ча-ша-то-нет'],['Ш','','----','ша-ро-ва-ра'],['Щ','Q','--.-','ща-вам-не-ша'],['Ь','X','-..-','то-мяг-кий-знак'],['Ы','Y','-.--','ы-не-на-до'],['Э','','..-..','э-ле-рон-чи-ки'],['Ю','','..--','ю-ли-а-на'],['Я','','.-.-','я-мал-я-мал']
];
export const letters = rows.map(([ru,en,code,chant])=>({ru,en,code,chant}));
export const digits = ['-----','.----','..---','...--','....-','.....','-....','--...','---..','----.'].map((code,i)=>({ru:String(i),en:String(i),code,chant:''}));
export const displayCode = code => code.replaceAll('.', '·').replaceAll('-', '−');
export function normalizeCode(text){return text.trim().replace(/[·•]/g,'.').replace(/[−—]/g,'-').replace(/\s*\/\s*/g,' / ').replace(/\s+/g,' ').trim();}
export function alphabet(lang, numbers=false){return [...letters.filter(x=>x[lang]),...(numbers?digits:[])];}
export function normalize(text,lang){return text.toUpperCase().replaceAll('Ё','Е').replaceAll('Ъ','Ь').trim().replace(/\s+/g,' ');}
export function encode(text,lang){const map=new Map(alphabet(lang,true).map(x=>[x[lang],x.code]));return normalize(text,lang).split('').map(c=>c===' '?'/':map.get(c)??'?').join(' ');}
export function decode(text,lang){const code=normalizeCode(text);if(!code)return '';const map=new Map(alphabet(lang,true).map(x=>[x.code,x[lang]]));return code.split(' / ').map(w=>w.split(' ').map(c=>map.get(c)??'?').join('')).join(' ');}
export function schedule(code,unit){let time=0;const tones=[];for(const word of normalizeCode(code).split(' / ')){for(const letter of word.split(' ')){for(const symbol of letter){if(!'.-'.includes(symbol))continue;const duration=unit*(symbol==='.'?1:3);tones.push({time,duration});time+=duration+unit;}time+=2*unit;}time+=4*unit;}return {tones,duration:Math.max(0,time-7*unit)};}
export function classify(duration,unit){return duration>=2*unit?'-':'.';}
