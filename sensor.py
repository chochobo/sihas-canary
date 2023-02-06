from __future__ import annotations
from dataclasses import dataclass

from datetime import timedelta
from typing import Callable, Dict, List, Optional
import asyncio

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL,
    STATE_CLASS_TOTAL_INCREASING,
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
    ENERGY_WATT_HOUR,
    LIGHT_LUX,
    PERCENTAGE,
    POWER_WATT,
    ELECTRIC_POTENTIAL_VOLT,
    ELECTRIC_CURRENT_AMPERE,
    FREQUENCY_HERTZ,
    TEMP_CELSIUS,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from typing_extensions import Final

from .const import (
    CONF_CFG,
    CONF_IP,
    CONF_MAC,
    CONF_TYPE,
    DEFAULT_PARALLEL_UPDATES,
    ICON_POWER_METER,
    SIHAS_PLATFORM_SCHEMA,
)
from .sihas_base import SihasProxy
from .util import register_put_u32

SCAN_INTERVAL = timedelta(seconds=5)

PARALLEL_UPDATES = DEFAULT_PARALLEL_UPDATES
PLATFORM_SCHEMA = SIHAS_PLATFORM_SCHEMA

AQM_GENERIC_SENSOR_DEFINE: Final = {
    "humidity": {
        "uom": PERCENTAGE,
        "value_handler": lambda r: round(r[1] / 10, 1),
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": STATE_CLASS_MEASUREMENT,
        "sub_id": "humidity",
    },
    "temperature": {
        "uom": TEMP_CELSIUS,
        "value_handler": lambda r: round(r[0] / 10, 1),
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": STATE_CLASS_MEASUREMENT,
        "sub_id": "temperature",
    },
    "illuminance": {
        "uom": LIGHT_LUX,
        "value_handler": lambda r: r[6],
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": STATE_CLASS_MEASUREMENT,
        "sub_id": "illuminance",
    },
    "co2": {
        "uom": CONCENTRATION_PARTS_PER_MILLION,
        "value_handler": lambda r: r[2],
        "device_class": SensorDeviceClass.CO2,
        "state_class": STATE_CLASS_MEASUREMENT,
        "sub_id": "co2",
    },
    "pm25": {
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "value_handler": lambda r: r[3],
        "device_class": SensorDeviceClass.PM25,
        "state_class": STATE_CLASS_MEASUREMENT,
        "sub_id": "pm25",
    },
    "pm10": {
        "uom": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "value_handler": lambda r: r[4],
        "device_class": SensorDeviceClass.PM10,
        "state_class": STATE_CLASS_MEASUREMENT,
        "sub_id": "pm10",
    },
    "tvoc": {
        "uom": CONCENTRATION_PARTS_PER_BILLION,
        "value_handler": lambda r: r[5],
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        "state_class": STATE_CLASS_MEASUREMENT,
        "sub_id": "tvoc",
    },
}

PMM_KEY_POWER: Final = "power"
PMM_KEY_THIS_MONTH_ENERGY: Final = "this_month_energy"
PMM_KEY_THIS_DAY_ENERGY: Final = "this_day_energy"
PMM_KEY_TOTAL: Final = "total_energy"
PMM_KEY_VOLTAGE: Final = "voltage"
PMM_KEY_CURRENT: Final = "current"
PMM_KEY_POWER_FACTOR: Final = "power_factor"
PMM_KEY_FREQUENCY: Final = "frequency"
PMM_KEY_THIS_HOUR_ENERGY: Final = "this_hour_energy"
PMM_KEY_BEFORE_HOUR_ENERGY: Final = "before_hour_energy"
PMM_KEY_YESTERDAY_ENERGY: Final = "yesterday_energy"
PMM_KEY_LAST_MONTH_ENERGY: Final = "last_month_energy"
PMM_KEY_TWO_MONTHS_AGO_ENERGY: Final = "two_months_ago_energy"
PMM_KEY_THIS_MONTH_FORECAST_ENERGY: Final = "this_month_forecast_energy"

@dataclass
class PmmConfig:
    nuom: str
    value_handler: Callable
    device_class: SensorDeviceClass
    state_class: str
    sub_id: str


PMM_GENERIC_SENSOR_DEFINE: Final = {
    PMM_KEY_POWER: PmmConfig(
        nuom=POWER_WATT,
        value_handler=lambda r: r[2],
        device_class=SensorDeviceClass.POWER,
        state_class=STATE_CLASS_MEASUREMENT,
        sub_id=PMM_KEY_POWER,
    ),
    PMM_KEY_THIS_MONTH_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[10] * 10,
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_THIS_MONTH_ENERGY,
    ),
    PMM_KEY_THIS_DAY_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[8] * 10,
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_THIS_DAY_ENERGY,
    ),
    PMM_KEY_TOTAL: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: register_put_u32(r[40], r[41]),
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL_INCREASING,
        sub_id=PMM_KEY_TOTAL,
    ),
    PMM_KEY_VOLTAGE: PmmConfig(
        nuom=ELECTRIC_POTENTIAL_VOLT,
        value_handler=lambda r: r[0] / 10,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=STATE_CLASS_MEASUREMENT,
        sub_id=PMM_KEY_VOLTAGE,
    ),
    PMM_KEY_CURRENT: PmmConfig(
        nuom=ELECTRIC_CURRENT_AMPERE,
        value_handler=lambda r: r[1] / 100,
        device_class=SensorDeviceClass.CURRENT,
        state_class=STATE_CLASS_MEASUREMENT,
        sub_id=PMM_KEY_CURRENT,
    ),
    PMM_KEY_POWER_FACTOR: PmmConfig(
        nuom=PERCENTAGE,
        value_handler=lambda r: r[3] / 10,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=STATE_CLASS_MEASUREMENT,
        sub_id=PMM_KEY_POWER_FACTOR,
    ),
    PMM_KEY_FREQUENCY: PmmConfig(
        nuom=FREQUENCY_HERTZ,
        value_handler=lambda r: r[4] / 10,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=STATE_CLASS_MEASUREMENT,
        sub_id=PMM_KEY_FREQUENCY,
    ),
    PMM_KEY_THIS_HOUR_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[6] * 10 + r[16],
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_THIS_HOUR_ENERGY,
    ),
    PMM_KEY_BEFORE_HOUR_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[7] * 10,
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_BEFORE_HOUR_ENERGY,
    ),
    PMM_KEY_YESTERDAY_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[9] * 10,
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_YESTERDAY_ENERGY,
    ),
    PMM_KEY_LAST_MONTH_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[11] * 10,
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_LAST_MONTH_ENERGY,
    ),
    PMM_KEY_TWO_MONTHS_AGO_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[12] * 10,
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_TWO_MONTHS_AGO_ENERGY,
    ),
    PMM_KEY_THIS_MONTH_FORECAST_ENERGY: PmmConfig(
        nuom=ENERGY_WATT_HOUR,
        value_handler=lambda r: r[13] * 10,
        device_class=SensorDeviceClass.ENERGY,
        state_class=STATE_CLASS_TOTAL,
        sub_id=PMM_KEY_THIS_MONTH_FORECAST_ENERGY,
    ),
}

# r[0] : 전압
# r[1] : 전류
# r[2] : 현재 전력량
# r[3] : 역률(/10)
# r[4] : 주파수
# r[5] : 측정기 누적 전력량(kW로 소숫점 이하 절사)
# r[6] : 현시간 사용량
# r[7] : 전시간 사용량
# r[8] : 당일 사용량
# r[9] : 전일 사용량
# r[10] : 당월 사용량
# r[11] : 전월 사용량
# r[12] : 전전월 사용량
# r[13] : 당월 예측 전력량
# r[14] : 누진 1단계 적용 전력량
# r[15] : 누진 2단계 적용 전력량
# r[16] : 현재 20분간 사용량(w)
# r[17] : 지난 20분간 사용량(w)
# r[18] : 부하 연결 상태(1: on, 0: off)
# r[19] : 부하 연결 상태 기준 전력
# r[20] : 검침일
# r[21] : 당일 목표 전력(*10 을 해야 앱과 동일)
# r[22] : 당월 목표 전력(*10 을 해야 앱과 동일)
# r[23] : 전력량 리셋?
# r[24] : CT 타입(0:외장형, 1:내장형)
# r[25] : LCD 방향 표시(0:정방향, 1:역방향)
# r[26] : 스마트폰 푸시 알림(0: 미사용, 1: 사용, 2:일목표치, 4: 월목표치, 8:월목표치 16+2048=2064: 월예측 누진1단계, 32+4096=4128:월사용 누진1단계, 64: 월예측 누진2단계, 128: 월사용 누진2단계) 각숫자의 합으로 조합됨
# r[41] * 65536 + r[40] : 측정기 누적 전력(앱상의 w값으로 절사 없음)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    if entry.data[CONF_TYPE] == "PMM":
        device = Device("PMM300", entry)

        pmm = Pmm300(device,
            ip=entry.data[CONF_IP],
            mac=entry.data[CONF_MAC],
            device_type=entry.data[CONF_TYPE],
            config=entry.data[CONF_CFG],
        )
        async_add_entities(pmm.get_sub_entities())

    elif entry.data[CONF_TYPE] == "AQM":
        aqm = Aqm300(
            ip=entry.data[CONF_IP],
            mac=entry.data[CONF_MAC],
            device_type=entry.data[CONF_TYPE],
            config=entry.data[CONF_CFG],
        )
        async_add_entities(aqm.get_sub_entities())


class Device:
    """Dummy roller (device for HA) for Hello World example."""

    def __init__(self, name, config):
        """Init dummy roller."""
        self._id = f"{name}_{config.entry_id}"
        self._name = name
        self._callbacks = set()
        self._loop = asyncio.get_event_loop()
        # Reports if the roller is moving up or down.
        # >0 is up, <0 is down. This very much just for demonstration.

        # Some static information about this device
        self.firmware_version = "2.03"
        self.model = "PMM300"
        self.manufacturer = "sihas"

    @property
    def name(self):
        return self._name

    @property
    def device_id(self):
        """Return ID for roller."""
        return self._id

    def register_callback(self, callback):
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback):
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    # In a real implementation, this library would call it's call backs when it was
    # notified of any state changeds for the relevant device.
    async def publish_updates(self):
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

    def publish_updates(self):
        """Schedule call all registered callbacks."""
        for callback in self._callbacks:
            callback()

class Pmm300(SihasProxy):
    def __init__(
        self,
        device,
        ip: str,
        mac: str,
        device_type: str,
        config: int,
        name: Optional[str] = None,
    ):
        super().__init__(
            ip=ip,
            mac=mac,
            device_type=device_type,
            config=config,
        )
        self.name = name
        self._device = device

    def get_sub_entities(self) -> List[Entity]:
        return [
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_POWER]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_THIS_MONTH_ENERGY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_THIS_DAY_ENERGY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_TOTAL]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_VOLTAGE]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_CURRENT]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_POWER_FACTOR]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_FREQUENCY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_THIS_HOUR_ENERGY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_BEFORE_HOUR_ENERGY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_YESTERDAY_ENERGY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_LAST_MONTH_ENERGY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_TWO_MONTHS_AGO_ENERGY]),
            PmmVirtualSensor(self, PMM_GENERIC_SENSOR_DEFINE[PMM_KEY_THIS_MONTH_FORECAST_ENERGY]),
        ]


class PmmVirtualSensor(SensorEntity):
    _attr_icon = ICON_POWER_METER

    def __init__(self, proxy: Pmm300, conf: PmmConfig) -> None:
        super().__init__()
        self._proxy = proxy
        self._device = proxy._device
        self._attr_available = self._proxy._attr_available
        self._attr_unique_id = f"{proxy.device_type}-{proxy.mac}-{conf.sub_id}"
        self._attr_native_unit_of_measurement = conf.nuom
        self._attr_name = f"{proxy.name} #{conf.sub_id}" if proxy.name else self._attr_unique_id
        self._attr_device_class = conf.device_class
        self._attr_state_class = conf.state_class
        self._name = conf.sub_id

        self.value_handler: Callable = conf.value_handler

    def update(self):
        self._proxy.update()
        self._attr_native_value = self.value_handler(self._proxy.registers)
        self._attr_available = self._proxy._attr_available

    @property
    def name(self):
        return self._name

    @property
    def device_info(self):
        """Information about this entity/device."""
        return {
            "identifiers": {("PMM300", self._device.device_id)},
            # If desired, the name for the device could be different to the entity
            "name": self._device.name,
            "sw_version": self._device.firmware_version,
            "model": self._device.model,
            "manufacturer": self._device.manufacturer
        }

class Aqm300(SihasProxy):
    """Representation of AQM-300

    offer below measurements:
        - co2
        - humidity
        - illuminance
        - pm10
        - pm25
        - temperature

    and it will appear seperatly as AqmVirtualSensor
    """

    def __init__(
        self,
        ip: str,
        mac: str,
        device_type: str,
        config: int,
        name: Optional[str] = None,
    ):
        super().__init__(
            ip=ip,
            mac=mac,
            device_type=device_type,
            config=config,
        )
        self.name = name

    def get_sub_entities(self) -> List[Entity]:
        return [
            AqmVirtualSensor(self, AQM_GENERIC_SENSOR_DEFINE["co2"]),
            AqmVirtualSensor(self, AQM_GENERIC_SENSOR_DEFINE["pm25"]),
            AqmVirtualSensor(self, AQM_GENERIC_SENSOR_DEFINE["pm10"]),
            AqmVirtualSensor(self, AQM_GENERIC_SENSOR_DEFINE["tvoc"]),
            AqmVirtualSensor(self, AQM_GENERIC_SENSOR_DEFINE["humidity"]),
            AqmVirtualSensor(self, AQM_GENERIC_SENSOR_DEFINE["illuminance"]),
            AqmVirtualSensor(self, AQM_GENERIC_SENSOR_DEFINE["temperature"]),
        ]


class AqmVirtualSensor(SensorEntity):
    def __init__(self, proxy: Aqm300, conf: Dict) -> None:
        super().__init__()

        self._proxy = proxy
        self._attr_available = self._proxy._attr_available
        self._attr_unique_id = f"{proxy.device_type}-{proxy.mac}-{conf['device_class']}"
        self._attr_native_unit_of_measurement = conf["uom"]
        self._attr_name = f"{proxy.name} #{conf['sub_id']}" if proxy.name else self._attr_unique_id
        self._attr_device_class = conf["device_class"]
        self._attr_state_class = conf["state_class"]

        self.value_handler: Callable = conf["value_handler"]

    def update(self):
        self._proxy.update()
        self._attr_native_value = self.value_handler(self._proxy.registers)
        self._attr_available = self._proxy._attr_available
