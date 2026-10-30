export const themes=[
  {id:'paper',name:'Бумага',colors:['#eee9dc','#dce0ce','#333b2c'],accent:'#62734a'},
  {id:'midnight',name:'Полночь',colors:['#121826','#1c2638','#e1e9f5'],accent:'#80a7ff'},
  {id:'ocean',name:'Глубокий океан',colors:['#09252d','#123943','#d1f4f0'],accent:'#51c7b5'},
  {id:'plum',name:'Сливовый бархат',colors:['#251c2f','#35273f','#f2deee'],accent:'#d6a1d0'},
  {id:'graphite',name:'Графит',colors:['#191b1e','#272a2f','#e5e5e6'],accent:'#b5c5a0'},
  {id:'peach',name:'Персиковый свет',colors:['#fff2e7','#f1dfd2','#533e37'],accent:'#b35f48'},
  {id:'blueprint',name:'Чертёж',colors:['#102b50','#183b65','#dceeff'],accent:'#8ddcfc'},
  {id:'acid',name:'Кислотный поп',colors:['#efff81','#d8eb70','#30224d'],accent:'#7547ba'},
  {id:'mars',name:'Марсианская пыль',colors:['#2b1918','#402622','#f3d6b3'],accent:'#efa277'},
  {id:'neon-city',name:'Неоновый город',colors:['#130925','#ff59de','#4deaff'],accent:'#f15bda'},
  {id:'neon-circuit',name:'Неоновый контур',colors:['#061b24','#77ff96','#ff7cdb'],accent:'#45f5c5'},
  {id:'cyberpunk',name:'Cyberpunk',colors:['#11101a','#262034','#fff2b4'],accent:'#f8e51b'},
]

export function accentText(hex){const rgb=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2]>.58?'#152019':'#ffffff'}
