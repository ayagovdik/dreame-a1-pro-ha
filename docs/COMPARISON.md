# Сравнение интеграций для Dreame A1 Pro (Home Assistant)

Для **Dreame A1 Pro** (`dreame.mower.g2422`) — что пробовать и что брать в свой форк.

| | [keysim86/ha-dreame-mower](https://github.com/keysim86/ha-dreame-mower) | [antondaubert/dreame-mower](https://github.com/antondaubert/dreame-mower) | [andiwirz/com.mova-dreame.mower](https://github.com/andiwirz/com.mova-dreame.mower) (Homey) | Наш `dreame_a1-ha` |
|--|------------------|----------------------|------------------|------------|
| **Платформа** | HA ✅ | HA ✅ | Homey only | HA (в разработке) |
| **A1 Pro** | Официально тестируется автором | В списке моделей | В README ошибочно «A2» 🟡 | Целевая модель |
| **MOVA** | Нет | Да | Да | Планируется |
| **Карта** | PNG renderer (Pillow), **fallback истории** | SVG camera, batch MAP | Нет картинки, zone picker | SVG + refresh button |
| **Текущая зона** | `sensor.current_zone_id` / `_state` | Частично / task attrs | Picker | `sensor.current_zone` |
| **Кнопки зон** | `button.mow_zone_<id>` динамически | `select` + services | Device card | `select` + service |
| **Зависимости** | Тяжёлые (numpy, pillow, miio, mini_racer) | Лёгкие (requests, mqtt) | — | Лёгкие |
| **Происхождение** | Fork [nicolasglg/dreame-mower-a1-pro](https://github.com/nicolasglg/dreame-mower-a1-pro) ← vacuum lineage | Fork bhuebschen | С нуля + packet capture | Fork antondaubert |

---

## keysim86/ha-dreame-mower — главное для A1 Pro

Автор **сам владеет A1 Pro**. В CHANGELOG 1.1.22 — исправления под ваш сценарий:

### Проблема: batch MAP пустой

A1 Pro часто отдаёт `MAP.*` с **`mowingAreas.value=[]`** (базовая карта без зон).  
`antondaubert` может «успешно» распарсить пустую геометрию → **нет зон и пустая camera**.

**keysim86:**

```text
_try_build_map_from_batch()
  → jeśli empty_map → return False
  → _try_use_last_history_map()
       → format stref z pliku historii
       → albo _build_map_data_from_path_json() (GPS track)
```

### Проблема: карта только как трек

Historia sesji: `{"map":[{"area":N,"data":[[x,y],...]}]}` — не полигоны зон, а **GPS-трек**.  
Parser `_build_map_data_from_path_json` рисует синтетический сегмент «Trawnik» + путь.

### Сущности (из README)

- `lawn_mower` — start/stop/dock  
- `camera.map` — зоны с **именами**, no-go  
- `sensor.current_zone_id` / `current_zone_state`  
- `button.mow_zone_<id>` — косить зону одной кнопкой  
- `switch` DND, статистика кошения (MIHIS-подобное из истории)  
- `binary_sensor.has_saved_map`

### Загрузка MAP (лучше чем «всё сразу»)

```python
# device.py — пакетами по 32 ключа MAP.0..MAP.31, MAP.32.. и т.д.
for batch_start in range(0, 256, 32):
    response = cloud.get_batch_device_datas([f"MAP.{i}" for i in range(...)])
```

### Парсинг зон (близко к реальному JSON A1 Pro)

- `mowingAreas` как `dict` с `value` **или** как list  
- `forbiddenAreas`, `contours`  
- bbox из точек, если `boundary` нулевой  
- имена зон → `Segment.custom_name`

### Минусы keysim86

- Наследие **пылесосного** стека (`map.py` ~9k строк) — тяжёлая установка  
- Много сервисов (`mower_goto`, `remote_control`) могут не работать на газонокосилке  
- **MOVA не поддерживается**  
- `iot_class: cloud_polling` — другая архитектура, чем MQTT-heavy antondaubert  
- Документация API хуже, чем у Homey

---

## antondaubert/dreame-mower

**Плюсы:** MQTT realtime, легче, MOVA, multizone service, активное сообщество.  
**Минусы для A1 Pro:** если batch MAP пустой — карта/зоны не появятся без доработки (как у вас).

---

## Homey (andiwirz)

**Плюсы:** лучший **справочник протокола** (op 102/103, CFG, PRE, mapIndex).  
**Минусы:** не HA.

См. [HOMEY_REFERENCE.md](./HOMEY_REFERENCE.md).

---

## Рекомендация для вас (A1 Pro + HA)

1. **Сначала попробуйте** [keysim86/ha-dreame-mower](https://github.com/keysim86/ha-dreame-mower) через HACS custom repo — это ближе всего к «работает на A1 Pro из коробки» с картой и текущей зоной.  
2. Если не устроит вес/лишние сущности — переносим в `dreame_a1-ha`:
   - fallback historii + path JSON (**keysim86**)
   - chunked MAP fetch (**keysim86**)
   - op-коды и CFG (**Homey**)
   - лёгкий SVG renderer (**antondaubert**)

---

## Что портировать в `dreame_a1-ha` (приоритет)

| # | Источник | Что |
|---|----------|-----|
| 1 | keysim86 | `empty_map` → fallback history |
| 2 | keysim86 | `_build_map_data_from_path_json` |
| 3 | keysim86 | MAP batch по 32 ключа |
| 4 | keysim86 | `current_zone_id` + имя зоны |
| 5 | keysim86 | dynamic `button` / улучшенный `select` по зонам |
| 6 | Homey | `mapIndex` в поле `p` команд 2:50 |
| 7 | Homey | CFG: WRP, DND, PRE cutting height |
| 8 | antondaubert | MQTT + live pose на SVG |

Файлы keysim86 для чтения:

- `custom_components/dreame_mower/dreame/device.py` — `_build_map_from_cloud_data`, `_try_build_map_from_batch`, `_build_map_data_from_zones_json`, `_build_map_data_from_path_json`
- `custom_components/dreame_mower/sensor.py` — `current_zone_*`
- `custom_components/dreame_mower/button.py` — `DreameMowerZoneMowButton`
- `CHANGELOG.md` — 1.1.20–1.1.22
