import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv
from esphome.types import ConfigType

from . import CONF_MR60BHA2_ID, MR60BHA2Component

DEPENDENCIES = ["seeed_mr60bha2"]

CONF_FIRMWARE_VERSION = "firmware_version"
CONF_DEBUG_LOG = "debug_log"
CONF_LAST_UNKNOWN_FRAME = "last_unknown_frame"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_MR60BHA2_ID): cv.use_id(MR60BHA2Component),
        cv.Optional(CONF_FIRMWARE_VERSION): text_sensor.text_sensor_schema(
            icon="mdi:chip",
        ),
        cv.Optional(CONF_DEBUG_LOG): text_sensor.text_sensor_schema(
            icon="mdi:bug-outline",
        ),
        cv.Optional(CONF_LAST_UNKNOWN_FRAME): text_sensor.text_sensor_schema(
            icon="mdi:help-rhombus-outline",
        ),
    }
)


async def to_code(config: ConfigType) -> None:
    component = await cg.get_variable(config[CONF_MR60BHA2_ID])

    setters = {
        CONF_FIRMWARE_VERSION: "set_firmware_version_text_sensor",
        CONF_DEBUG_LOG: "set_debug_log_text_sensor",
        CONF_LAST_UNKNOWN_FRAME: "set_last_unknown_frame_text_sensor",
    }

    for key, setter_name in setters.items():
        if sensor_config := config.get(key):
            sens = await text_sensor.new_text_sensor(sensor_config)
            cg.add(getattr(component, setter_name)(sens))
