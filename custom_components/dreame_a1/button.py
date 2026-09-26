"""Button entities for Dreame Mower actions."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import DreameMowerCoordinator
from .entity import DreameMowerEntity

_LOGGER = logging.getLogger(__name__)

# (item_key, icon, translation_key)
_RESET_BUTTONS = [
    ("blade", "mdi:scissors-cutting", "reset_blade"),
    ("brush", "mdi:brush", "reset_brush"),
    ("robot", "mdi:robot", "reset_robot_maintenance"),
]

# (unique_key, icon, translation_key, action)
_REMOTE_BUTTONS = [
    ("remote_start", "mdi:gamepad-variant", "remote_start", "start"),
    ("remote_forward", "mdi:arrow-up-bold", "remote_forward", "forward"),
    ("remote_left", "mdi:arrow-left-bold", "remote_left", "left"),
    ("remote_stop", "mdi:stop", "remote_stop", "stop"),
    ("remote_right", "mdi:arrow-right-bold", "remote_right", "right"),
    ("remote_back", "mdi:arrow-down-bold", "remote_back", "back"),
]

REMOTE_STEP_VELOCITY = 80
REMOTE_STEP_ROTATION = 90


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Dreame Mower buttons from a config entry."""
    coordinator: DreameMowerCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities: list[ButtonEntity] = [
        DreameMowerResetConsumableButton(coordinator, item, icon, translation_key)
        for item, icon, translation_key in _RESET_BUTTONS
    ]
    entities.append(DreameMowerRefreshMapButton(coordinator))
    entities.append(DreameMowerDockWithoutStoppingButton(coordinator))
    entities.append(DreameMowerFindButton(coordinator))
    entities.append(DreameMowerMowSelectedZoneButton(coordinator))
    entities.extend(
        DreameMowerRemoteButton(coordinator, key, icon, translation_key, action)
        for key, icon, translation_key, action in _REMOTE_BUTTONS
    )
    async_add_entities(entities)


class DreameMowerResetConsumableButton(DreameMowerEntity, ButtonEntity):
    """Button that resets one CMS consumable counter to zero."""

    def __init__(
        self,
        coordinator: DreameMowerCoordinator,
        item: str,
        icon: str,
        translation_key: str,
    ) -> None:
        super().__init__(coordinator, f"reset_consumable_{item}")
        self._item = item
        self._attr_icon = icon
        self._attr_translation_key = translation_key

    async def async_press(self) -> None:
        """Reset the consumable counter and refresh coordinator data."""
        await self.coordinator.device.reset_consumable_counter(self._item)
        try:
            await self.coordinator.async_fetch_consumable_data()
        except Exception as ex:
            _LOGGER.warning("Consumable refresh after reset failed: %s", ex)


class DreameMowerRefreshMapButton(DreameMowerEntity, ButtonEntity):
    """Reload map geometry from the Dreame cloud batch API."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        super().__init__(coordinator, "refresh_map")
        self._attr_icon = "mdi:map-sync"
        self._attr_translation_key = "refresh_map"

    async def async_press(self) -> None:
        """Fetch vector map and notify camera/select entities."""
        updated = await self.hass.async_add_executor_job(
            self.coordinator.device.fetch_vector_map
        )
        if not updated:
            _LOGGER.warning(
                "Map refresh for %s returned no data — check that a map exists in Dreamehome and HA logs for dreame_a1",
                self.coordinator.device_name,
            )
            return
        await self.coordinator.async_request_refresh()
        _LOGGER.info(
            "Map refreshed for %s: %d zone(s), map id=%s",
            self.coordinator.device_name,
            len(self.coordinator.zones),
            self.coordinator.current_map_id,
        )


class DreameMowerDockWithoutStoppingButton(DreameMowerEntity, ButtonEntity):
    """Button that sends the mower to dock without cancelling the active task."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        super().__init__(coordinator, "dock_without_stopping")
        self._attr_icon = "mdi:home-battery"
        self._attr_translation_key = "dock_without_stopping"

    async def async_press(self) -> None:
        """Send mower to dock without stopping the current task."""
        if not await self.coordinator.device.dock_without_stopping():
            _LOGGER.error("Failed to send mower to dock without stopping")


class DreameMowerFindButton(DreameMowerEntity, ButtonEntity):
    """Make the mower beep."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        super().__init__(coordinator, "find")
        self._attr_icon = "mdi:bullhorn"
        self._attr_translation_key = "find"

    async def async_press(self) -> None:
        if not await self.coordinator.device.find_mower():
            _LOGGER.error("Failed to find mower")


class DreameMowerMowSelectedZoneButton(DreameMowerEntity, ButtonEntity):
    """Start mowing the zone currently selected in the Zone dropdown."""

    def __init__(self, coordinator: DreameMowerCoordinator) -> None:
        super().__init__(coordinator, "mow_selected_zone")
        self._attr_icon = "mdi:mower"
        self._attr_translation_key = "mow_selected_zone"

    async def async_press(self) -> None:
        zone_id = self.coordinator.selected_zone_id
        if zone_id is None:
            _LOGGER.error("No zone selected")
            return
        if not await self.coordinator.device.start_mowing_zones([zone_id]):
            _LOGGER.error("Failed to start zone mowing for zone %s", zone_id)


class DreameMowerRemoteButton(DreameMowerEntity, ButtonEntity):
    """One joystick step or enter/leave remote-control mode."""

    def __init__(
        self,
        coordinator: DreameMowerCoordinator,
        key: str,
        icon: str,
        translation_key: str,
        action: str,
    ) -> None:
        super().__init__(coordinator, key)
        self._action = action
        self._attr_icon = icon
        self._attr_translation_key = translation_key

    async def async_press(self) -> None:
        device = self.coordinator.device
        ok = False
        if self._action == "start":
            ok = await device.start_remote_control()
        elif self._action == "stop":
            ok = await device.stop_remote_control()
        elif self._action == "forward":
            ok = await device.remote_move(REMOTE_STEP_VELOCITY, 0)
        elif self._action == "back":
            ok = await device.remote_move(-REMOTE_STEP_VELOCITY, 0)
        elif self._action == "left":
            ok = await device.remote_move(0, -REMOTE_STEP_ROTATION)
        elif self._action == "right":
            ok = await device.remote_move(0, REMOTE_STEP_ROTATION)
        if not ok:
            _LOGGER.error("Remote-control action %s failed", self._action)
