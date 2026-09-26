# Dreame A1 / A1 Pro — интеграция для Home Assistant

Кастомная интеграция для роботизированных газонокосилок **Dreame A1, A1 Pro, A2** и совместимых **MOVA**. Это не форк `dreame-vacuum`: пылесосная интеграция [Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum) **не поддерживает** газонокосилки и не умеет зоны, карты участка и сценарии кошения.

Протокол и облачное API взяты из сообщества ([antondaubert/dreame-mower](https://github.com/antondaubert/dreame-mower), [bhuebschen/dreame-mower](https://github.com/bhuebschen/dreame-mower)) и доработаны под полноценную работу с A1 Pro в HA.

## Возможности

| Функция | Описание |
|--------|----------|
| **Текущая зона** | Сенсор `current_zone` — в какой зоне косит робот прямо сейчас (+ очередь зон в атрибутах) |
| **Текущая карта** | Сенсор `current_map` — активная карта участка |
| **Живая карта** | Камера с позицией робота и треком |
| **Управление** | `lawn_mower`: старт, пауза, док, стоп |
| **Режимы** | Select: карта, режим (весь участок / край / зона / spot), зона, контур |
| **Мультизона** | Сервис `dreame_a1.start_zone_mowing` — несколько зон подряд без возврата на базу |
| **Статус и батарея** | Сенсоры, коды ошибок, прогресс кошения, расходники |

## Установка

### Через HACS (рекомендуется)

1. HACS → Integrations → ⋮ → **Custom repositories**
2. URL: `https://github.com/ayagovdik/dreame-a1-pro-ha`
3. Категория: **Integration**
4. Установить **Dreame A1 Pro Lawn Mower**
5. Перезагрузить Home Assistant
6. Настройки → Устройства и службы → **Добавить интеграцию** → **Dreame A1 Pro Lawn Mower**
7. Войти теми же учётными данными, что в приложении **Dreamehome** (для A1 Pro — не Mi Home)

### Вручную

Скопируйте папку `custom_components/dreame_a1` в `config/custom_components/` вашего Home Assistant и перезагрузите HA.

> **Важно:** не ставьте одновременно `dreame-vacuum` и `dreame_a1` на одну и ту же газонокосилку — возможны конфликты MQTT/облака.

## Управление зонами

### В интерфейсе HA

1. **Mowing mode** → выберите `Zone`
2. **Zone** → нужная зона
3. Нажмите **Start mowing** на сущности `lawn_mower`

### Несколько зон за один выезд

```yaml
action: dreame_a1.start_zone_mowing
target:
  entity_id: lawn_mower.a1_pro
data:
  zone_ids: [1, 3, 5]
```

ID зон видны в атрибутах сущности `lawn_mower` (`zones`) или в select **Zone**.

### Автоматизация по текущей зоне

```yaml
trigger:
  - platform: state
    entity_id: sensor.a1_pro_current_zone
    to: "Зона 1"  # имя из карты в приложении
action:
  - service: notify.mobile_app_phone
    data:
      message: "Робот начал косить зону 1"
```

## Сущности после настройки

- `lawn_mower.*` — управление
- `sensor.*_current_zone` — текущая зона
- `sensor.*_current_map` — текущая карта
- `camera.*` — карта участка
- `select.*` — карта, режим, зона, контур
- `button.*` — обновить карту, загрузить историю

## Карта не появляется?

В `antondaubert/dreame-mower` (и в старом `bhuebschen/dreame-mower`) карта — это **не отдельная «Map»-интеграция**, а:

1. Сущность **`camera.*`** (часто `…_map_camera`) — SVG-карта участка.
2. Select **`Map`**, **`Zone`** и т.д. — появляются только после загрузки карты из облака.

Если после установки «пара сенсоров есть, карты нет» — почти всегда **не подтянулись данные MAP** с сервера Dreame.

**Проверьте по шагам:**

1. В приложении **Dreamehome** карта участка создана и робот онлайн.
2. В HA: Настройки → Устройства → ваш робот → есть ли **`camera.…_map_camera`**? Если сущности камеры нет — смотрите **Журнал** на ошибки `Invalid entity ID` (имя робота с `+`, пробелами, кириллицей в названии устройства).
3. Сущности **Map / Zone** серые или пустые → карта из batch API не загрузилась. Включите отладку:
   ```yaml
   logger:
     logs:
       custom_components.dreame_a1: debug
   ```
   Перезагрузите интеграцию и ищите `No batch map data` / `no parseable MAP data`.
4. На панель добавьте карточку **Picture** или **Picture entity** и выберите `camera.…_map_camera` (сама по себе карта на дашборд не попадает).
5. Управление: карточка **Lawn mower** на сущности `lawn_mower.…` (старт/пауза/док), не отдельные кнопки на главном экране.

В форке `dreame_a1` в этом репозитории добавлена кнопка **«Обновить карту»** для повторной загрузки без перезагрузки HA.

## Документация для разработчиков

- [docs/COMPARISON.md](docs/COMPARISON.md) — сравнение **keysim86**, antondaubert, Homey для A1 Pro.
- [docs/HOMEY_REFERENCE.md](docs/HOMEY_REFERENCE.md) — протокол из [andiwirz/com.mova-dreame.mower](https://github.com/andiwirz/com.mova-dreame.mower).
- [docs/ROADMAP.md](docs/ROADMAP.md) — план портирования в `dreame_a1`.

**Если у вас A1 Pro и antondaubert не даёт карту** — сначала посмотрите [keysim86/ha-dreame-mower](https://github.com/keysim86/ha-dreame-mower): автор косит на том же железе и чинил пустой `mowingAreas` + fallback на историю сессий.

## Ограничения

- Облачное подключение (как в официальном приложении); локального API у Dreame нет.
- Ручное джойстик-управление по Bluetooth в HA пока не реализовано.
- Неофициальная интеграция: используйте на свой риск.

## Лицензия

MIT. Основано на [antondaubert/dreame-mower](https://github.com/antondaubert/dreame-mower).
