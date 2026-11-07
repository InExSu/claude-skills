---
name: game-ui-probe
license: MIT
description: >
  Browser-based UI probing for games and web apps: screenshots, computed styles,
  camera directions, HUD geometry, and "element is visible and inside the frame"
  checks. Use when a visual or layout defect must be proven by a machine instead of
  "looks fine": pause overlay too dark, HUD in a column instead of a row, mirrors
  showing the wrong direction, a panel off-screen, a hidden element still visible.
  «проверь UI», «зеркало показывает не туда», «HUD не на месте», «пауза слишком
  тёмная», «элемент за краем экрана», «проверь скриншотом».
  Do NOT use for pure logic bugs with no DOM/canvas — those belong to unit tests.
---

# Game UI Probe

Браузерная проба UI отвечает на вопросы, которые юнит-тесты не видят: где элемент, какого он размера, куда смотрит камера, что реально применил каскад CSS. Вердикт выносится числами и assert, скриншот — доказательство для человека.

## Когда применять

- Визуальный дефект: затенение, размытие, цвет, перекрытие, обрезка.
- Раскладка: HUD, панели, кнопки, мобильный viewport.
- 3D-сцены: направление камер, видимость объектов, попадание в кадр.
- «Элемент есть в DOM, но его не видно» и наоборот.
- Проверка, что убранный элемент действительно отсутствует.

Не применять: чистая логика, парсеры, математика — там юнит-тесты дешевле и стабильнее.

## Обязательный каркас пробы

```js
import { firefox } from 'playwright';

const UA = 'Mozilla/5.0 ... Chrome/128.0.0.0 Safari/537.36';
const browser = await firefox.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 800 },   // фиксированный
  userAgent: UA,                            // иначе щит .htaccess режет ассеты
  locale: 'ru-RU',                          // фиксированный язык
});
const page = await ctx.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push('[pageerror] ' + e.message));
page.on('console', (m) => { if (m.type() === 'error') errors.push('[error] ' + m.text()); });
page.on('requestfailed', (r) => errors.push('[requestfailed] ' + r.url()));

await page.goto(url, { waitUntil: 'load', timeout: 60000 });
await page.waitForTimeout(4000);
await page.click('#btn-start');
```

Правила каркаса:

1. Фиксируй viewport, userAgent и locale. Иначе геометрия и тексты «плавают».
2. Собирай `pageerror`, `console.error`, `requestfailed` и вали гейт на них.
3. Жди готовности игры явно (хук `getState`/`loaded`), а не «sleep на глаз».
4. Для состояния используй штатный хук (`window.__GAME`), а не клики наугад.
5. Повтори прогон 3 раза: 3/3 — доказательство, 2/3 — флейк.

## Проверки, которые надо уметь

### Геометрия и раскладка

```js
const rects = await page.evaluate(() => {
  const sels = ['.hud-score', '.hud-speed', '.hud-best', '.hud-lane'];
  return sels.map((sel) => {
    const el = document.querySelector(sel);
    if (!el) return { sel, missing: true };
    const r = el.getBoundingClientRect();
    return {
      sel,
      left: Math.round(r.left), right: Math.round(r.right),
      top: Math.round(r.top), bottom: Math.round(r.bottom),
      cy: Math.round((r.top + r.bottom) / 2),
    };
  });
});
```

Проверяй: разброс вертикальных центров, нижний край, долю ширины экрана, перекрытия, выход за viewport.

**Цепляйся за структурный блок.** `#hud-score` может быть `span` с числом внутри `.hud-score`; измерение по id даст ложный результат.

### Computed style

```js
const cs = await page.evaluate(() => {
  const el = document.querySelector('#paused');
  const s = getComputedStyle(el);
  return { backgroundImage: s.backgroundImage, backdropFilter: s.backdropFilter };
});
```

Проверяй альфы `rgba(...)` и `blur(Npx)` регуляркой; сравнивай с порогами из спецификации. Не читай исходный CSS — каскад и медиазапросы важнее.

### Видимость и отсутствие

```js
const visible = await page.evaluate(() => {
  const el = document.querySelector('#briefing');
  if (!el) return false;
  const s = getComputedStyle(el);
  return !el.classList.contains('hidden') && s.display !== 'none' && s.visibility !== 'hidden';
});
```

Отрицательный контроль обязателен: убранное зеркало должно отсутствовать, скрытый брифинг — быть скрытым, пустой блок — пустым.

### 3D-камеры и объекты

```js
const m = await page.evaluate(() => window.__GAME.mirrorState());
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
// заднее зеркало смотрит назад: dot <= -0.85
```

Проверяй `getWorldDirection`, dot с основной камерой, `visible`, экранные доли через `project(camera)`. Для убранных узлов — `sideCount === 0` и отсутствие полей.

### Скриншоты

```js
await page.screenshot({ path: 'artifacts/ui.png' });
```

Скриншот прикладывай к PR, но не делай его единственным доказательством. Он нужен человеку; машина проверяет числа.

## Чек-лист перед коммитом

- [ ] Viewport, userAgent и locale зафиксированы.
- [ ] Ошибки консоли/сети собираются и валят пробу.
- [ ] Измеряется структурный блок, а не вложенный id.
- [ ] Геометрия проверяется числами (центры, края, доли, перекрытия).
- [ ] Computed style читается через `getComputedStyle`.
- [ ] Для 3D — dot направлений и `visible`, для убранного — отсутствие полей.
- [ ] Есть отрицательный контроль (элемент отсутствует/скрыт, когда должен).
- [ ] Прогон 3/3 без флейков.
- [ ] Скриншот приложен к PR как доказательство, а не как тест.

## Антипаттерны

- `assert(el !== null)` вместо проверки видимости и геометрии.
- Ожидание «пока трафик сам создаст сцену» вместо телепорта состояния.
- Проверка по id вложенного элемента.
- Один прогон и вердикт «работает».
- Скриншот без чисел.
- Игнорирование `console.error` и `requestfailed`.
