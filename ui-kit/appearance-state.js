import {themes} from './themes.js';

export const appearanceDefaults = {theme:'paper',accent:'#62734a',fontScale:100,radius:8,density:'comfortable',panelWidth:280};
export function sanitizeAppearance(input = {}, legacyTheme = 'paper') {
  if (!input || typeof input !== 'object' || Array.isArray(input)) input = {};
  const themeId = input.theme ?? (legacyTheme === 'dark' ? 'graphite' : legacyTheme);
  const theme = themes.find(t => t.id === themeId) ?? themes[0];
  const result = {...appearanceDefaults, theme:theme.id, accent:theme.accent};
  if (typeof input.accent === 'string' && /^#[0-9a-f]{6}$/i.test(input.accent)) result.accent = input.accent;
  if (input.density === 'compact') result.density = 'compact';
  for (const [key,min,max] of [['fontScale',90,120],['radius',0,18],['panelWidth',240,400]]) {
    if (typeof input[key] === 'number' && Number.isFinite(input[key])) result[key] = Math.max(min,Math.min(max,Math.round(input[key])));
  }
  return result;
}
