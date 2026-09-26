# Roadmap: `dreame_a1` ← портирование из Homey

Основано на [HOMEY_REFERENCE.md](./HOMEY_REFERENCE.md).

## Фаза 0 — починить то, что у вас не работает (порт с keysim86)

- [ ] **Пустой batch MAP:** если `mowingAreas.value=[]` → не считать успехом, fallback на историю сессий ([keysim86](https://github.com/keysim86/ha-dreame-mower) `device.py` 1.1.22)
- [ ] **История GPS:** parser `map[0].data` как трек, если в файле нет полигонов зон
- [ ] **MAP batch:** запрос чанками `MAP.0..31`, `MAP.32..` (не один пустой `get_batch([])`)
- [ ] Логи: preview MAP chunks, `empty_map` flag
- [ ] **`mapIndex` в `p`** (из Homey) для команд зон
- [ ] Сенсоры `current_zone_id` + имя зоны (как keysim86)
- [ ] Кнопка Refresh map + документация Lovelace

## Фаза 1 — управление как в приложении

- [ ] Select «режим кошения»: all / zone / edge_all / edge_zone / spot
- [ ] Сервисы: `start_edge_mowing`, `go_to_maintenance`, `find_mower`
- [ ] Сенсор `map_index` + атрибут списка зон из fallback-парсера

## Фаза 2 — настройки робота (CFG)

- [ ] `getCFG()` при старте и раз в 5–10 мин
- [ ] `number`: cutting height (PRE[4]), volume (VOL)
- [ ] `switch`: child lock, frost, rain (WRP), DND, low speed night
- [ ] `button`: reset consumable counters (если есть в протоколе HA)

## Фаза 3 — статистика и автоматизации

- [ ] MIHIS → сенсоры total area / time / sessions
- [ ] Триггеры HA: mowing started/completed, battery low, error (аналог flow cards)
- [ ] Опционально: AI obstacle notification (AOP + разбор после сессии)

## Фаза 4 — полировка

- [ ] Тесты на fixture из `dreame-mower` + сырые `MAP.*` из Homey issues
- [ ] HACS, README RU, скриншоты Lovelace
- [ ] Issue template «пришлите model + фрагмент MAP.info»
