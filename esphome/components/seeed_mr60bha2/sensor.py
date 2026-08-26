import esphome.codegen as cg
from esphome.components import sensor
import esphome.config_validation as cv
from esphome.const import (
    CONF_DISTANCE,
    DEVICE_CLASS_DISTANCE,
    ICON_COUNTER,
    ICON_HEART_PULSE,
    ICON_PULSE,
    ICON_SIGNAL,
    STATE_CLASS_MEASUREMENT,
    UNIT_BEATS_PER_MINUTE,
    UNIT_CENTIMETER,
)
from esphome.types import ConfigType

from . import CONF_MR60BHA2_ID, MR60BHA2Component

DEPENDENCIES = ["seeed_mr60bha2"]

MAX_TARGETS = 3

CONF_BREATH_RATE = "breath_rate"
CONF_HEART_RATE = "heart_rate"
CONF_NUM_TARGETS = "num_targets"
CONF_TOTAL_PHASE = "total_phase"
CONF_BREATH_PHASE = "breath_phase"
CONF_HEART_PHASE = "heart_phase"
CONF_RANGE_FLAG = "range_flag"
CONF_POINT_CLOUD_COUNT = "point_cloud_count"
CONF_ALT_X = "alternative_x"
CONF_ALT_Y = "alternative_y"
CONF_STATUS_CODE = "status_code"
CONF_FIRMWARE_PROJECT = "firmware_project"
CONF_FIRMWARE_MAJOR = "firmware_major"
CONF_FIRMWARE_SUB = "firmware_sub"
CONF_FIRMWARE_MODIFIED = "firmware_modified"
CONF_PACKET_RATE = "packet_rate"
CONF_PHASE_PACKET_RATE = "phase_packet_rate"
CONF_TARGET_PACKET_RATE = "target_packet_rate"
CONF_POINT_CLOUD_PACKET_RATE = "point_cloud_packet_rate"
CONF_LAST_PACKET_AGE = "last_packet_age"
CONF_LAST_PHASE_AGE = "last_phase_age"
CONF_LAST_TARGET_AGE = "last_target_age"
CONF_LAST_POINT_CLOUD_AGE = "last_point_cloud_age"
CONF_VALID_FRAME_COUNT = "valid_frame_count"
CONF_HEADER_CHECKSUM_ERRORS = "header_checksum_errors"
CONF_DATA_CHECKSUM_ERRORS = "data_checksum_errors"
CONF_OVERSIZE_FRAME_ERRORS = "oversize_frame_errors"
CONF_UNKNOWN_FRAME_COUNT = "unknown_frame_count"
CONF_LAST_FRAME_ID = "last_frame_id"
CONF_LAST_FRAME_TYPE = "last_frame_type"
CONF_LAST_UNKNOWN_TYPE = "last_unknown_type"


def measurement_schema(
    *,
    unit=None,
    accuracy=2,
    icon=None,
    device_class=None,
):
    kwargs = {
        "accuracy_decimals": accuracy,
        "state_class": STATE_CLASS_MEASUREMENT,
    }
    if unit is not None:
        kwargs["unit_of_measurement"] = unit
    if icon is not None:
        kwargs["icon"] = icon
    if device_class is not None:
        kwargs["device_class"] = device_class
    return sensor.sensor_schema(**kwargs)


schema = {
    cv.GenerateID(CONF_MR60BHA2_ID): cv.use_id(MR60BHA2Component),
    cv.Optional(CONF_BREATH_RATE): measurement_schema(
        unit="breaths/min",
        accuracy=1,
        icon=ICON_PULSE,
    ),
    cv.Optional(CONF_HEART_RATE): measurement_schema(
        unit=UNIT_BEATS_PER_MINUTE,
        accuracy=1,
        icon=ICON_HEART_PULSE,
    ),
    cv.Optional(CONF_DISTANCE): measurement_schema(
        unit=UNIT_CENTIMETER,
        accuracy=2,
        icon=ICON_SIGNAL,
        device_class=DEVICE_CLASS_DISTANCE,
    ),
    cv.Optional(CONF_NUM_TARGETS): measurement_schema(
        accuracy=0,
        icon=ICON_COUNTER,
    ),
    cv.Optional(CONF_TOTAL_PHASE): measurement_schema(
        unit="rad",
        accuracy=5,
        icon="mdi:sine-wave",
    ),
    cv.Optional(CONF_BREATH_PHASE): measurement_schema(
        unit="rad",
        accuracy=5,
        icon="mdi:sine-wave",
    ),
    cv.Optional(CONF_HEART_PHASE): measurement_schema(
        unit="rad",
        accuracy=5,
        icon="mdi:sine-wave",
    ),
    cv.Optional(CONF_RANGE_FLAG): measurement_schema(
        accuracy=0,
        icon="mdi:signal-variant",
    ),
    cv.Optional(CONF_POINT_CLOUD_COUNT): measurement_schema(
        accuracy=0,
        icon="mdi:dots-hexagon",
    ),
    cv.Optional(CONF_ALT_X): measurement_schema(
        unit="m",
        accuracy=3,
        icon="mdi:axis-x-arrow",
    ),
    cv.Optional(CONF_ALT_Y): measurement_schema(
        unit="m",
        accuracy=3,
        icon="mdi:axis-y-arrow",
    ),
    cv.Optional(CONF_STATUS_CODE): measurement_schema(
        accuracy=0,
        icon="mdi:list-status",
    ),
    cv.Optional(CONF_FIRMWARE_PROJECT): measurement_schema(
        accuracy=0,
        icon="mdi:chip",
    ),
    cv.Optional(CONF_FIRMWARE_MAJOR): measurement_schema(
        accuracy=0,
        icon="mdi:chip",
    ),
    cv.Optional(CONF_FIRMWARE_SUB): measurement_schema(
        accuracy=0,
        icon="mdi:chip",
    ),
    cv.Optional(CONF_FIRMWARE_MODIFIED): measurement_schema(
        accuracy=0,
        icon="mdi:chip",
    ),
    cv.Optional(CONF_PACKET_RATE): measurement_schema(
        unit="Hz",
        accuracy=2,
        icon="mdi:speedometer",
    ),
    cv.Optional(CONF_PHASE_PACKET_RATE): measurement_schema(
        unit="Hz",
        accuracy=2,
        icon="mdi:sine-wave",
    ),
    cv.Optional(CONF_TARGET_PACKET_RATE): measurement_schema(
        unit="Hz",
        accuracy=2,
        icon="mdi:target-account",
    ),
    cv.Optional(CONF_POINT_CLOUD_PACKET_RATE): measurement_schema(
        unit="Hz",
        accuracy=2,
        icon="mdi:dots-hexagon",
    ),
    cv.Optional(CONF_LAST_PACKET_AGE): measurement_schema(
        unit="s",
        accuracy=2,
        icon="mdi:timer-sand",
    ),
    cv.Optional(CONF_LAST_PHASE_AGE): measurement_schema(
        unit="s",
        accuracy=2,
        icon="mdi:timer-sand",
    ),
    cv.Optional(CONF_LAST_TARGET_AGE): measurement_schema(
        unit="s",
        accuracy=2,
        icon="mdi:timer-sand",
    ),
    cv.Optional(CONF_LAST_POINT_CLOUD_AGE): measurement_schema(
        unit="s",
        accuracy=2,
        icon="mdi:timer-sand",
    ),
    cv.Optional(CONF_VALID_FRAME_COUNT): measurement_schema(
        accuracy=0,
        icon="mdi:counter",
    ),
    cv.Optional(CONF_HEADER_CHECKSUM_ERRORS): measurement_schema(
        accuracy=0,
        icon="mdi:alert-circle-outline",
    ),
    cv.Optional(CONF_DATA_CHECKSUM_ERRORS): measurement_schema(
        accuracy=0,
        icon="mdi:alert-circle-outline",
    ),
    cv.Optional(CONF_OVERSIZE_FRAME_ERRORS): measurement_schema(
        accuracy=0,
        icon="mdi:alert-circle-outline",
    ),
    cv.Optional(CONF_UNKNOWN_FRAME_COUNT): measurement_schema(
        accuracy=0,
        icon="mdi:help-rhombus-outline",
    ),
    cv.Optional(CONF_LAST_FRAME_ID): measurement_schema(
        accuracy=0,
        icon="mdi:identifier",
    ),
    cv.Optional(CONF_LAST_FRAME_TYPE): measurement_schema(
        accuracy=0,
        icon="mdi:identifier",
    ),
    cv.Optional(CONF_LAST_UNKNOWN_TYPE): measurement_schema(
        accuracy=0,
        icon="mdi:help-rhombus-outline",
    ),
}

for index in range(1, MAX_TARGETS + 1):
    for prefix, icon in (("target", "mdi:target-account"), ("point", "mdi:dots-hexagon")):
        schema[cv.Optional(f"{prefix}_{index}_x")] = measurement_schema(
            unit="m", accuracy=3, icon="mdi:axis-x-arrow"
        )
        schema[cv.Optional(f"{prefix}_{index}_y")] = measurement_schema(
            unit="m", accuracy=3, icon="mdi:axis-y-arrow"
        )
        schema[cv.Optional(f"{prefix}_{index}_doppler_index")] = measurement_schema(
            accuracy=0, icon=icon
        )
        schema[cv.Optional(f"{prefix}_{index}_speed")] = measurement_schema(
            unit="m/s", accuracy=3, icon="mdi:speedometer"
        )
        schema[cv.Optional(f"{prefix}_{index}_distance")] = measurement_schema(
            unit="m", accuracy=3, icon="mdi:map-marker-distance"
        )
        schema[cv.Optional(f"{prefix}_{index}_angle")] = measurement_schema(
            unit="°", accuracy=2, icon="mdi:angle-acute"
        )
        schema[cv.Optional(f"{prefix}_{index}_cluster_id")] = measurement_schema(
            accuracy=0, icon="mdi:identifier"
        )

CONFIG_SCHEMA = cv.Schema(schema)


async def make_sensor(component, config, key, setter_name, *setter_args):
    if sensor_config := config.get(key):
        sens = await sensor.new_sensor(sensor_config)
        cg.add(getattr(component, setter_name)(*setter_args, sens))


async def to_code(config: ConfigType) -> None:
    component = await cg.get_variable(config[CONF_MR60BHA2_ID])

    direct_setters = {
        CONF_BREATH_RATE: "set_breath_rate_sensor",
        CONF_HEART_RATE: "set_heart_rate_sensor",
        CONF_DISTANCE: "set_distance_sensor",
        CONF_NUM_TARGETS: "set_num_targets_sensor",
        CONF_TOTAL_PHASE: "set_total_phase_sensor",
        CONF_BREATH_PHASE: "set_breath_phase_sensor",
        CONF_HEART_PHASE: "set_heart_phase_sensor",
        CONF_RANGE_FLAG: "set_range_flag_sensor",
        CONF_POINT_CLOUD_COUNT: "set_point_cloud_count_sensor",
        CONF_ALT_X: "set_alternative_x_sensor",
        CONF_ALT_Y: "set_alternative_y_sensor",
        CONF_STATUS_CODE: "set_status_code_sensor",
        CONF_FIRMWARE_PROJECT: "set_firmware_project_sensor",
        CONF_FIRMWARE_MAJOR: "set_firmware_major_sensor",
        CONF_FIRMWARE_SUB: "set_firmware_sub_sensor",
        CONF_FIRMWARE_MODIFIED: "set_firmware_modified_sensor",
        CONF_PACKET_RATE: "set_packet_rate_sensor",
        CONF_PHASE_PACKET_RATE: "set_phase_packet_rate_sensor",
        CONF_TARGET_PACKET_RATE: "set_target_packet_rate_sensor",
        CONF_POINT_CLOUD_PACKET_RATE: "set_point_cloud_packet_rate_sensor",
        CONF_LAST_PACKET_AGE: "set_last_packet_age_sensor",
        CONF_LAST_PHASE_AGE: "set_last_phase_age_sensor",
        CONF_LAST_TARGET_AGE: "set_last_target_age_sensor",
        CONF_LAST_POINT_CLOUD_AGE: "set_last_point_cloud_age_sensor",
        CONF_VALID_FRAME_COUNT: "set_valid_frame_count_sensor",
        CONF_HEADER_CHECKSUM_ERRORS: "set_header_checksum_errors_sensor",
        CONF_DATA_CHECKSUM_ERRORS: "set_data_checksum_errors_sensor",
        CONF_OVERSIZE_FRAME_ERRORS: "set_oversize_frame_errors_sensor",
        CONF_UNKNOWN_FRAME_COUNT: "set_unknown_frame_count_sensor",
        CONF_LAST_FRAME_ID: "set_last_frame_id_sensor",
        CONF_LAST_FRAME_TYPE: "set_last_frame_type_sensor",
        CONF_LAST_UNKNOWN_TYPE: "set_last_unknown_type_sensor",
    }

    for key, setter_name in direct_setters.items():
        await make_sensor(component, config, key, setter_name)

    indexed_fields = {
        "x": "x",
        "y": "y",
        "doppler_index": "doppler_index",
        "speed": "speed",
        "distance": "distance",
        "angle": "angle",
        "cluster_id": "cluster_id",
    }

    for index in range(MAX_TARGETS):
        yaml_index = index + 1
        for field, method_field in indexed_fields.items():
            await make_sensor(
                component,
                config,
                f"target_{yaml_index}_{field}",
                f"set_target_{method_field}_sensor",
                index,
            )
            await make_sensor(
                component,
                config,
                f"point_{yaml_index}_{field}",
                f"set_point_{method_field}_sensor",
                index,
            )
