// Add future tools here. Internal tools use a hash route; external tools use a URL.
export const tools = [
 {id:'morse',name:'AmuzMorse',category:'Обучение',tag:'ОТ ТОЧКИ ДО СЛОВА',description:'Услышь ритм. Запомни буквы. Передай первое сообщение.',url:'#morse',symbol:'· −',meta:'RU + EN · 6 режимов',featured:true},
 {id:'upscale',name:'AmuzUpscale',category:'Творчество',tag:'БОЛЬШЕ МАСШТАБА. БОЛЬШЕ ДЕТАЛЕЙ.',description:'Увеличивай фото нейросетью ×2 и ×4, уточняй контуры и сравнивай результат с оригиналом.',url:'#upscale',symbol:'↗',meta:'FSRCNN · ×2 / ×4 · PNG / JPG / WebP'},
 {id:'fetch',name:'AmuzFetch',category:'Медиа',tag:'СОХРАНИ МОМЕНТ',description:'Видео с YouTube и Instagram. Выбери качество, формат и забери файл со звуком.',url:'#download',symbol:'↙',meta:'YouTube · Instagram · 5 форматов'},
 {id:'ascii',name:'AmuzASCII',category:'Творчество',tag:'ИЗ ПИКСЕЛЕЙ — В СИМВОЛЫ',description:'Твоя студия ASCII-арта. Превращай фотографии и видео в характер.',url:'/ascii/',symbol:'@#',meta:'Фото · Видео · Экспорт'}
];
