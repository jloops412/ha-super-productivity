import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import CONF_HAS_TARGET, DEVICE_CLASS_OCCUPANCY
from esphome.types import ConfigType

from . import CONF_MR60BHA2_ID, MR60BHA2Component

DEPENDENCIES = ["seeed_mr60bha2"]

CONF_RADAR_DATA_VALID = "radar_data_valid"
CONF_VITAL_SIGNS_VALID = "vital_signs_valid"
CONF_PHASE_DATA_VALID = "phase_data_valid"
CONF_TARGET_DATA_VALID = "target_data_valid"
CONF_POINT_CLOUD_DATA_VALID = "point_cloud_data_valid"

CONFIG_SCHEMA = {
    cv.GenerateID(CONF_MR60BHA2_ID): cv.use_id(MR60BHA2Component),
    cv.Optional(CONF_HAS_TARGET): binary_sensor.binary_sensor_schema(
        device_class=DEVICE_CLASS_OCCUPANCY,
        icon="mdi:motion-sensor",
    ),
    cv.Optional(CONF_RADAR_DATA_VALID): binary_sensor.binary_sensor_schema(
        icon="mdi:check-network-outline",
    ),
    cv.Optional(CONF_VITAL_SIGNS_VALID): binary_sensor.binary_sensor_schema(
        icon="mdi:heart-pulse",
    ),
    cv.Optional(CONF_PHASE_DATA_VALID): binary_sensor.binary_sensor_schema(
        icon="mdi:sine-wave",
    ),
    cv.Optional(CONF_TARGET_DATA_VALID): binary_sensor.binary_sensor_schema(
        icon="mdi:target-account",
    ),
    cv.Optional(CONF_POINT_CLOUD_DATA_VALID): binary_sensor.binary_sensor_schema(
        icon="mdi:dots-hexagon",
    ),
}


async def to_code(config: ConfigType) -> None:
    component = await cg.get_variable(config[CONF_MR60BHA2_ID])

    setters = {
        CONF_HAS_TARGET: "set_has_target_binary_sensor",
        CONF_RADAR_DATA_VALID: "set_radar_data_valid_binary_sensor",
        CONF_VITAL_SIGNS_VALID: "set_vital_signs_valid_binary_sensor",
        CONF_PHASE_DATA_VALID: "set_phase_data_valid_binary_sensor",
        CONF_TARGET_DATA_VALID: "set_target_data_valid_binary_sensor",
        CONF_POINT_CLOUD_DATA_VALID: "set_point_cloud_data_valid_binary_sensor",
    }

    for key, setter_name in setters.items():
        if sensor_config := config.get(key):
            sens = await binary_sensor.new_binary_sensor(sensor_config)
            cg.add(getattr(component, setter_name)(sens))
