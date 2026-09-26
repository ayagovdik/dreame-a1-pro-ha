# Справочник: что перенести из [andiwirz/com.mova-dreame.mower](https://github.com/andiwirz/com.mova-dreame.mower)

Источник — **Homey**-приложение (JavaScript), не Home Assistant. Протокол облака **тот же**, что у `antondaubert/dreame-mower` / нашего `dreame_a1`. Документ для портирования в HA.

---

## 1. Важно понимать разницу платформ

| | Homey (`com.mova-dreame.mower`) | HA (`dreame_a1`) |
|--|--------------------------------|------------------|
| Язык | Node.js | Python |
| Статус | Polling `getDeviceData` + `listV2` каждые ~30 с | MQTT push + `get_batch_device_datas` при старте |
| Карта в UI | Нет картинки — **Zone/Spot picker** из `MAP.*` | `camera` (SVG) + `select` зон |
| Зрелость UI | Очень богатая карточка устройства | Базовое `lawn_mower` + сенсоры |
| Документация API | README ~370 строк, packet capture | В основном код + тесты |

**Вывод:** Homey — лучший **справочник команд и CFG**, не замена HA. Для A1 Pro в таблице тестов указан `dreame.mower.g2422` как «A2» — в HA это **A1 Pro** (опечатка в README Homey).

---

## 2. Облако: эндпоинты (подтверждено в `lib/MovaApi.js`)

Хост: `https://{region}.iot.dreame.tech` или `https://{region}.iot.mova-tech.com`, порт **13267**.

| Путь | Назначение |
|------|------------|
| `POST /dreame-auth/oauth/token` | Логин / refresh (`password` + MD5 с солью `RAylYC%fmSKp7%Tq`) |
| `POST /dreame-user-iot/iotuserbind/device/listV2` | Список устройств, `latestStatus`, `battery`, `bindDomain` |
| `POST /dreame-user-iot/iotuserdata/getDeviceData` | Poll: `SETTINGS.*`, `MAP.*`, OTA… (v2 игнорирует список siid/piid) |
| `POST /dreame-user-iot/iotuserdata/setDeviceData` | Запись MiOT-свойств (на v2 часто бесполезно) |
| `POST /dreame-iot-com{bindHost}/device/sendCommand` | Действия: `bindHost` = `-{первый сегмент bindDomain}` (напр. `-20000`) |

**Basic auth (оба бренда):** `Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg=`

**Регионы:** `eu`, `cn`, `us`, `sg` — префикс к хосту.

---

## 3. v2 API (A1 Pro, MOVA, A2, A3)

На новых газонокосилках:

- `getDeviceData` возвращает **словарь ключей** (`MAP.0`, `SETTINGS.0`, …), а не массив `{siid, piid, value}`.
- Прямая запись `setProperty(2, 109, height)` → **ошибка 10007**.
- Настройки и кошение — через **канал действий** `siid:2, aiid:50`.

Читать статус можно из **listV2** (`latestStatus`, `battery`) — Homey так и делает в poll.

---

## 4. Канал действий `2:50` — кошение (op-коды)

Формат элемента `in`: `{ m:'a', p:<mapIndex>, o:<opcode>, d:{...} }`.

| `o` | Действие | `d` | Примечание |
|-----|----------|-----|------------|
| **9** | Найти робота (звук) | `{}` | Вместо старого `siid:7` |
| **100** | Весь участок (HA) | `{ region_id:[mapId], area_id:[] }` | У Homey — `sendAction(5,1)` «start mowing» |
| **101** | Край участка | `{}` или `{ edge:[[zoneId, mapIdx]] }` | **Не** подставлять случайные contour ID — «zone unreachable» |
| **102** | Зоны | `{ region:[1,3,5] }` | Плоский массив ID, без пар |
| **103** | Spot | `{ area:[1001,1002] }` | ID spot ≥ 1000 |
| **108** | Обход границы без кошения | `{ edge:[[zoneId, mapIdx]] }` | Randpatrouille |
| **109** | Точка обслуживания | `{ point:[1] }` | |
| **200** | Сменить карту | `{ idx: mapIndex }` | HA: `set_current_map` |
| **201** | Применить spot | — | HA: `_build_apply_spot_selection_payload` |
| **214** | Создать spot-прямоугольник | `{ id:-1, points:[...] }` | 4 точки |

**Критично для HA:** поле `p` = **активный `mapIndex`** из `MAP` (regex `"mapIndex":N`). Сейчас в `dreame_a1` часто захардкожено `"p": 0` — при `mapIndex !== 0` команды могут не работать.

**Базовые команды (подтверждены):** `siid:5` — `aiid:1` start, `2` stop, `3` dock, `4` pause.

---

## 5. CFG — чтение и запись

**Читать всё:** `in: [{ m:'g', t:'CFG' }]` → `result.out[0].d`

**Писать ключ:** `in: [{ m:'s', t:'KEY', d:{...} }]`

| Ключ | SET | Описание |
|------|-----|----------|
| `CLS` | `{value:0\|1}` | Детский замок |
| `FDP` | `{value:0\|1}` | Защита от мороза |
| `WRP` | `{value, sen, time}` | Дождь: вкл, чувствительность 1–3, ожидание (часы) |
| `VOL` | `{value:0-100}` | Громкость |
| `DND` | `{value, time:[startMin,endMin]}` | Не беспокоить (минуты от полуночи) |
| `LOW` | `{value, time:[...]}` | Медленно ночью |
| `LIT` | `{value, time:[...], light:[s,w,c,e]}` | Подсветка LED |
| `BAT` | `{value:[return%, resume%, autoResume], type:'power'}` | Пороги батареи |
| `VOICE` | `{value:[4×0\|1]}` | Режимы голоса — **все 4 сразу** |
| `ATA` | `{value:[lift, mapAlarm, gps]}` | Антивор — **все 3 сразу** |
| `AOP` | `{value:0\|1}` | Фото препятствий AI |
| `PRE` | массив из 19 чисел | Настройки кошения — только **read-modify-write** |

**История:** `in: [{ m:'g', t:'MIHIS' }]` → `{ area: m², time: мин, count: сессий, start: unix }`

---

## 6. Массив PRE (19 элементов) — из SETTINGS

На v2 **PRE не читается** с устройства; Homey **собирает** из `SETTINGS.0` → `settings["0"]`:

| Индекс | Поле SETTINGS | Смысл |
|--------|---------------|--------|
| 3 | `efficientMode` | 0=Standard, 1=Efficient |
| 4 | `mowingHeight` | см × 10 → мм на слайдере |
| 5–18 | edge/obstacle/… | Край, LiDAR, AI bitmask и т.д. |

Запись высоты: изменить `pre[4]`, отправить `{ t:'PRE', d: preArray, m:'s' }`.

**Порт в HA:** `number` cutting height, `select` efficiency, опционально edge/obstacle через `writePRE`.

---

## 7. Парсинг MAP без полного JSON (из `device.js`)

Homey на каждом poll склеивает `MAP.0` + `MAP.1` + … и извлекает:

```javascript
// mapIndex — первое вхождение
/"mapIndex":(\d+)/

// Зоны 1–99 — секция mowingAreas до forbiddenAreas
/\[(\d{1,3}),\{/g  внутри mowingAreas

// Spots ≥1000 — секции: cleanSpots | spots | customAreas | virtualSpots
/\[(\d{4,5}),\{/g  или  /"id"\s*:\s*(\d{4,5})/
```

**Порт в HA:** fallback в `map_data_parser` или отдельный `extract_map_ids_from_batch()` если `parse_batch_map_data` вернул `None`, но ключи `MAP.*` есть — **это может быть причиной пустой карты у вас**.

---

## 8. SETTINGS — чанки

`SETTINGS.0` часто **обрезан**; нужно конкатенировать `SETTINGS.0` + `SETTINGS.1` до успешного `JSON.parse`.

Структура: массив карт → `[{ mode, settings: { "0": { mowingHeight, efficientMode, … } } }]`.

Индекс карты: `zones[_activeMapIndex]`.

**Порт в HA:** при poll/batch подтягивать SETTINGS для сенсоров настроек и сборки PRE.

---

## 9. Статусы (Homey `STATUS_MAP`)

| Код | Смысл |
|-----|--------|
| 1 | mowing |
| 3 | paused |
| 5 | returning |
| 6 | charging |
| 11 | mapping |
| 13 | docked / charging complete |
| 14 | updating |
| 23 | remote_control |
| 4 | error |

Совпадает с `dreame_a1` / EvotecIT enum.

---

## 10. Что уже есть в `dreame_a1` vs что взять из Homey

### Уже есть (близко к Homey)

- OAuth + cloud REST + MQTT
- `o:102` zone, `o:103` spot, `o:101` edge (contour pairs)
- Batch `MAP.*` → vector map + camera SVG
- `lawn_mower`, pause/dock, `start_zone_mowing` service
- Consumables, device codes, pose/live path

### Взять в первую очередь (высокий ROI)

1. **`mapIndex` в поле `p`** во всех task payload — из текущей карты.
2. **Fallback-парсер зон/spot** из сырого `MAP.*` (regex), если JSON-парсер падает.
3. **Подтягивать MAP/SETTINGS из poll** (`getDeviceData`), не только batch при старте.
4. **Кнопка «Обновить карту»** (уже добавлена) + лог при пустом MAP.
5. **Zone picker в HA** — `select` с опциями `all`, `zone_N`, `edge_all`, `edge_N` как в Homey.
6. **`getCFG` / CFG writers** — дождь, DND, высота через PRE, громкость, child lock.
7. **`goToMaintenancePoint`** (o:109), **findBot** (o:9).
8. **MIHIS** — сенсоры lifetime area/time/sessions.

### Средний приоритет

- Border patrol (o:108)
- Edge zone: `{ edge: [[zoneId, mapIndex]] }` — проверить формат vs HA `contour_ids`
- AI obstacle flow trigger + AOP
- Repair flow (перелогин без удаления устройства) — аналог reauth в HA
- SETTINGS → number/select для edge mowing options

### Низкий / осторожно

- `suppressFault` siid:4 — **80001 на MOVA/v2**
- `startManualMowing` siid:5 aiid:7 — не подтверждено
- Polling вместо MQTT — не заменять, только дополнить recovery

---

## 11. Архитектурная рекомендация для `dreame_a1`

```
dreame/cloud/          # MovaApi-порт: auth, listV2, getDeviceData, sendCommand
dreame/protocol/       # opcodes, CFG keys, PRE builder, MAP extractors
dreame/device.py       # оркестрация MQTT + периодический refresh MAP/SETTINGS
custom_components/     # HA entities
```

**Гибридный цикл обновления (как у Homey + HA):**

1. MQTT — realtime status, 2:56 zones, pose.
2. Каждые N минут или по кнопке: `get_batch_device_datas([])` + `getDeviceData` для MAP/SETTINGS.
3. При старте интеграции — оба канала.

---

## 12. Файлы Homey для чтения при портировании

| Файл | Содержание |
|------|------------|
| `lib/MovaApi.js` | Все API-вызовы и payload |
| `drivers/mower/device.js` | MAP regex, SETTINGS/PRE, poll, pickers, кнопки |
| `README.md` § API Reference | Таблицы siid/piid, op-codes, CFG |
| `app.json` | Полный список capabilities и flow cards |

---

## 13. Модели (справочно)

| model | Homey README | dreame_a1 `config_flow` |
|-------|--------------|-------------------------|
| `dreame.mower.p2255` | — | A1 |
| `dreame.mower.g2422` | «A2» 🟡 | **A1 Pro** |
| `dreame.mower.g2408` | — | A2 |
| `mova.mower.g2529d` | LiDAX 1200 ✅ | — |

---

## 14. Риски при портировании

- Отправлять **неверный op** или **edge ID не из карты** → робот может зависнуть/ошибка (предупреждение автора Homey).
- Писать **неполный** `VOICE`/`ATA`/`PRE` — сброс других полей.
- Игнорировать **bindDomain** → `sendCommand` на неверный host → 80001.

---

*Сгенерировано для репозитория `dreame-a1-ha`. Источник: MIT-совместимый анализ публичного кода [andiwirz/com.mova-dreame.mower](https://github.com/andiwirz/com.mova-dreame.mower). При публикации своего форка указать credits.*
