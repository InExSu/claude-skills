# Формат файлов DrakonHub (справочник)

Получено из исходников DrakonHub (`drakonhub_desktop`, `src/src/static/js/drakon_canvas.js`,
`dh2common.js`, `libs/drakongen.js`) и официальных примеров.

## 1. Валидация при импорте (`dh2common.checkJsonContent`)

Импортер принимает файл, только если:
- верхний уровень — объект, `items` — объект;
- `name`, `params`, `type`, `description` — строка (если есть);
- `style` — **строка**, содержащая JSON;
- каждый item — объект; `text`/`content`, `secondary` — строки; `style` — JSON-строка;
- ключ item не пустая строка.

После этого редактор пытается построить холст; при структурной ошибке — «Error in diagram structure».

## 2. Верхний уровень

| Поле | Тип | Обяз. | Смысл |
|---|---|---|---|
| `items` | object | да | `id -> item` |
| `type` | string | нет | `"drakon"` (алгоритм), `"graf"` (ментальная карта), `"free"` (свободная схема), `"basic"` |
| `name` | string | нет | имя диаграммы = текст заголовка |
| `params` | string | нет | формальные параметры (HTML) |
| `description` | string | нет | описание/ресурсы |
| `style` | JSON string | нет | тема оформления |
| `keywords` | object | нет | служебное |
| `access` | string | нет | `"read"` / `"write"` |

## 3. Item

Общие поля: `type`, `content`, `one`, `two`, `side`, `flag1`, `branchId`, `style`,
`secondary`, `link`, `ordinal`, `parent`, `treeType`, `left/top/width/height/px/py/zIndex`
(только свободные элементы).

Связи:
- `one` — вниз по вертелу;
- `two` — вправо (вопрос/вариант/параллельный поток);
- `side` — ссылка на `duration` (у `action`, `question`, `select`, `insertion`, `simpleinput`,
  `simpleoutput`, `shelf`, `process`, `input`, `output`);
- `link` — гиперссылка иконки;
- `flag1` — у `question`: `1` → `one`=Да, `two`=Нет; `0` → наоборот.
  У `group-duration` (свободный элемент): сторона привязки.

Текст `content` — строка, допускается HTML (`<p>`, `<strong>`, `<br>`), переносы строк как `\n`.
Пустой `content` у `question`, `select`, `loopbegin` ломает генерацию кода.

## 4. Полный список `type`

Потоковые («выровненные» на вертеле):
`action`, `question`, `select`, `case`, `branch`, `address`, `loopbegin`, `loopend`,
`insertion`, `comment`, `simpleinput`, `simpleoutput`, `shelf`, `input`, `output`,
`process`, `drakon-image`.

Служебные: `header` (id `header`), `params` (id `params`), `end`, `junction`,
`arrow-loop`, `parbegin`, `parend`.

Длительность/время: `duration`, `pause`, `timer`, `ctrlstart`, `ctrlend`.

Свободные (координатные): `callout`, `conclusion`, `group-duration`, `rectangle`,
`circle`/`ellipse`, `line`, `arrow`, `triangle`, `hexagon`, `polyline`, `frame`, `text`,
`image`, `drakon-image`.

Ментальные карты (`.graf`): `ridea` (корень), `idea`, `header`, `conclusion`, `callout`.

Типов `foreach`, `start`, `begin` в файле **не существует**.

## 5. Шаблоны конструкций

### Силуэт

```json
"b0": {"type":"branch","branchId":0,"content":"Часть 1","one":"1"},
"b1": {"type":"branch","branchId":1,"content":"Часть 2","one":"9"}
```
Вход — минимальный `branchId`. Переход на ветку: `one`/`two` указывают на id `branch`.

### Вопрос

```json
"q": {"type":"question","flag1":1,"one":"yes_id","two":"no_id","content":"Данные корректны?"}
```

### Выбор (select/case)

```json
"s":  {"type":"select","content":"Тип устройства?","one":"c1"},
"c1": {"type":"case","content":"Большой экран","one":"a1","two":"c2"},
"c2": {"type":"case","content":"Ноутбук","one":"a2","two":"c3"},
"c3": {"type":"case","content":"","one":"a3"}        // «остальные случаи»
```

### Цикл

```json
"lb": {"type":"loopbegin","content":"Повторить 10 раз","one":"body1"},
"body1": {"type":"action","content":"Поднять штангу","one":"q"},
"q": {"type":"question","flag1":0,"one":"le","two":"after","content":"Устал?"},
"le": {"type":"loopend","one":"after"}
```
Генератор идёт от `loopbegin.one` по цепочке `one`, пока не встретит `loopend`;
выход из цикла — `loopend.one`.

### Длительность действия

```json
"a": {"type":"action","content":"Стирка","one":"next","side":"d1"},
"d1": {"type":"duration","content":"20 мин"}
```

### Свободная плашка (callout)

```json
"c": {"type":"callout","left":610,"top":70,"width":110,"height":40,
      "content":"микрограммы","style":"{\"iconBack\":\"#ffffff\"}",
      "px":-75,"py":50,"zIndex":1}
```

### Ментальная карта (.graf)

```json
{"type":"graf","items":{
  "root":{"type":"header","treeType":"treeview"},
  "2":{"type":"idea","content":"Австралия","parent":"root","treeType":"treeview","ordinal":1}
}}
```

## 6. Стили

`style` — JSON-строка. Ключи: `iconBack`, `iconBorder`, `color`, `lines`, `internalLine`,
`borderWidth`, `lineWidth`, `font` (напр. `"bold 16px Arimo"`), `commentBack`, `shadowColor`.
Цвета — `#rrggbb` или имена CSS.
