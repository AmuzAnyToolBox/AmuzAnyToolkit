const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));

export function pointerSplit(clientX,left,width) {
  return width>0?clamp((clientX-left)/width*100,0,100):50;
}

export function imageSplit(percent,viewportLeft,viewportWidth,imageLeft,imageWidth) {
  return imageWidth>0?clamp((viewportLeft+viewportWidth*percent/100-imageLeft)/imageWidth*100,0,100):50;
}

export function viewDimensions(width,height,boxWidth,boxHeight,zoom) {
  const scale=zoom==='fit'?Math.min(boxWidth/width,boxHeight/height,1):zoom/100;
  return {width:Math.max(1,Math.round(width*scale)),height:Math.max(1,Math.round(height*scale)),scale};
}
