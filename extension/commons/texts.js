export function hasChineseText(text) {
  return /[\u4e00-\u9fff]/.test(text);
}
