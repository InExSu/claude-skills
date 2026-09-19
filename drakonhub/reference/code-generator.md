# Генератор кода DrakonHub (`drakongen.js`)

Кнопка «ИИ промпт» и генерация псевдокода/сценариев в DrakonHub работают
через `src/src/static/libs/drakongen.js`. Это **отдельный** проход по
диаграмме: он накладывает требования, которых нет ни в
`scripts/drakon_tool.py check`, ни в `scripts/drakon_try.py render`.

Диаграмма может открываться, не виснуть и проходить валидатор — и при этом
не собираться в псевдокод.

## Формат ошибки

Ошибка приходит как текст + имя файла + id иконки:

```
Выход из цикла должен вести в точку сразу за его концом
ai_Pobisk: обработка одной задачи ИИ-агентом.drakon
le
```

Первая строка — сообщение, вторая — имя диаграммы, третья — **id иконки,
к которой претензия** (здесь `le` — это `loopend`).

## Тексты проверок

Исходник — `src/src/static/libs/drakongen.js`. Переводы собраны в объекте
рядом с английскими строками; по русскому тексту ошибки ищите английский
ключ, а по нему — место в коде.

| Сообщение (RU) | Ключ (EN) | Где |
|---|---|---|
| Выход из цикла должен вести в точку сразу за его концом | An exit from the loop must lead to the point right after the loop end | `buildTree`, ветка `loopend` |
| Ошибка парсинга JSON | Error parsing JSON | `prepareDrakonDiagram` |

## «Выход из цикла должен вести в точку сразу за его концом»

Самая частая ошибка. Проверка в `buildTree`:

```js
} else if (node.type == "loopend") {
    if (stopId !== afterLoop) {
        onError(
            "An exit from the loop must lead to the point right after the loop end",
            node.id
        )
    }
    return
}
```

Обход тела цикла идёт так:

```js
} else if (node.type == "loopbegin") {
    var end = nodes[node.end]
    buildTree(nodes, node.one, transformed.body, node.end, end.one, onError)
    next = node.next;
}
```

`buildTree(nodes, nodeId, body, stopId, afterLoop, onError)` — четвёртый
аргумент `stopId` говорит «здесь тело заканчивается», пятый `afterLoop` —
«куда ведёт выход из цикла». Дойдя до `loopend`, генератор требует, чтобы
ожидаемый конец тела совпал с точкой после цикла.

На практике это означает: **из тела цикла нельзя выходить мимо `loopend`.**
Если у вопроса внутри цикла `two` уводит сразу на другую ветку, часть
путей приводит генератор в `loopend` с чужим `stopId` — отсюда ошибка.

### Как правильно

Все выходы из тела цикла (включая `two` вопросов и последние `action`)
ведут **в `loopend`**. Разбор причины выхода делается **после** него — в
отдельной ветке, на которую указывает `loopend.one`:

```
"15": {"type":"question","flag1":1,"content":"Модель ответила?","one":"16","two":"le"},
"le": {"type":"loopend","one":"bAsk"},
"bAsk": {"type":"branch","branchId":2,"content":"Проверка решения","one":"15x"},
"15x": {"type":"question","flag1":1,"content":"Модель ответила?","one":"16x","two":"bWait"},
```

Здесь вопрос, с которого начался выход, повторяется уже после цикла — так
сохраняется логика «почему вышли», и генератор проходит.

## Как проверить файл, не открывая редактор

Генератор — браузерный модуль, ему нужен `DOMParser`. Проще всего вызвать
его в headless-браузере на странице `drakonhub.html` (wiring — § 5.2
`SKILL.md`):

```js
const d = /* объект диаграммы */;
try {
    const out = window.drakongen.toPseudocode(JSON.stringify(d), d.name, d.name + '.drakon', 'ru');
    console.log(out);
} catch (e) {
    console.log('msg:', e.message, '| nodeId:', e.nodeId);
}
```

Доступные функции: `toPseudocode`, `toTree`, `makeScenarios`,
`makeScenariosJson`, `toMindTree`, `toMindTreeJson`, `freeToText`.

Важно: `toPseudocode` принимает **строку** JSON, а не объект — иначе будет
«Ошибка парсинга JSON: drakonJson.trim is not a function».

Если `drakongen` не лежит в `window`, поднимите локальный сервер в корне
`drakonhub_desktop` (`python3 -m http.server`) и откройте
`http://127.0.0.1:8765/drakonhub.html` — так же, как делает
`scripts/drakon_try.py`.
