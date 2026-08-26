#pragma once

#include "esphome/core/component.h"
#include "esphome/core/hal.h"

#ifdef USE_BINARY_SENSOR
#include "esphome/components/binary_sensor/binary_sensor.h"
#endif
#ifdef USE_SENSOR
#include "esphome/components/sensor/sensor.h"
#endif
#ifdef USE_TEXT_SENSOR
#include "esphome/components/text_sensor/text_sensor.h"
#endif

#include "esphome/components/uart/uart.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace esphome::seeed_mr60bha2 {

static constexpr uint8_t MR60BHA2_FRAME_START = 0x01;
static constexpr size_t MR60BHA2_HEADER_SIZE = 8;
static constexpr size_t MR60BHA2_MAX_PAYLOAD_SIZE = 512;
static constexpr uint8_t MR60BHA2_MAX_TARGETS = 3;

static constexpr uint16_t MR60BHA2_TYPE_DEBUG_LOG = 0x0100;
static constexpr uint16_t MR60BHA2_TYPE_TARGET_INFO = 0x0A04;
static constexpr uint16_t MR60BHA2_TYPE_POINT_CLOUD = 0x0A08;
static constexpr uint16_t MR60BHA2_TYPE_PHASE = 0x0A13;
static constexpr uint16_t MR60BHA2_TYPE_BREATH_RATE = 0x0A14;
static constexpr uint16_t MR60BHA2_TYPE_HEART_RATE = 0x0A15;
static constexpr uint16_t MR60BHA2_TYPE_DISTANCE = 0x0A16;
static constexpr uint16_t MR60BHA2_TYPE_ALTERNATIVE_POSITION = 0x0A17;
static constexpr uint16_t MR60BHA2_TYPE_STATUS_CODE = 0x0A29;
static constexpr uint16_t MR60BHA2_TYPE_HUMAN_DETECTION = 0x0F09;
static constexpr uint16_t MR60BHA2_TYPE_FIRMWARE = 0xFFFF;

class MR60BHA2Component final : public Component, public uart::UARTDevice {
 public:
  float get_setup_priority() const override { return esphome::setup_priority::LATE; }
  void setup() override;
  void dump_config() override;
  void loop() override;

#ifdef USE_BINARY_SENSOR
  void set_has_target_binary_sensor(binary_sensor::BinarySensor *sensor) { this->has_target_binary_sensor_ = sensor; }
  void set_radar_data_valid_binary_sensor(binary_sensor::BinarySensor *sensor) {
    this->radar_data_valid_binary_sensor_ = sensor;
  }
  void set_vital_signs_valid_binary_sensor(binary_sensor::BinarySensor *sensor) {
    this->vital_signs_valid_binary_sensor_ = sensor;
  }
  void set_phase_data_valid_binary_sensor(binary_sensor::BinarySensor *sensor) {
    this->phase_data_valid_binary_sensor_ = sensor;
  }
  void set_target_data_valid_binary_sensor(binary_sensor::BinarySensor *sensor) {
    this->target_data_valid_binary_sensor_ = sensor;
  }
  void set_point_cloud_data_valid_binary_sensor(binary_sensor::BinarySensor *sensor) {
    this->point_cloud_data_valid_binary_sensor_ = sensor;
  }
#endif

#ifdef USE_SENSOR
#define MR60BHA2_SENSOR_SETTER(name) \
  void set_##name##_sensor(sensor::Sensor *sensor) { this->name##_sensor_ = sensor; }

  MR60BHA2_SENSOR_SETTER(breath_rate)
  MR60BHA2_SENSOR_SETTER(heart_rate)
  MR60BHA2_SENSOR_SETTER(distance)
  MR60BHA2_SENSOR_SETTER(num_targets)
  MR60BHA2_SENSOR_SETTER(total_phase)
  MR60BHA2_SENSOR_SETTER(breath_phase)
  MR60BHA2_SENSOR_SETTER(heart_phase)
  MR60BHA2_SENSOR_SETTER(range_flag)
  MR60BHA2_SENSOR_SETTER(point_cloud_count)
  MR60BHA2_SENSOR_SETTER(alternative_x)
  MR60BHA2_SENSOR_SETTER(alternative_y)
  MR60BHA2_SENSOR_SETTER(status_code)
  MR60BHA2_SENSOR_SETTER(firmware_project)
  MR60BHA2_SENSOR_SETTER(firmware_major)
  MR60BHA2_SENSOR_SETTER(firmware_sub)
  MR60BHA2_SENSOR_SETTER(firmware_modified)
  MR60BHA2_SENSOR_SETTER(packet_rate)
  MR60BHA2_SENSOR_SETTER(phase_packet_rate)
  MR60BHA2_SENSOR_SETTER(target_packet_rate)
  MR60BHA2_SENSOR_SETTER(point_cloud_packet_rate)
  MR60BHA2_SENSOR_SETTER(last_packet_age)
  MR60BHA2_SENSOR_SETTER(last_phase_age)
  MR60BHA2_SENSOR_SETTER(last_target_age)
  MR60BHA2_SENSOR_SETTER(last_point_cloud_age)
  MR60BHA2_SENSOR_SETTER(valid_frame_count)
  MR60BHA2_SENSOR_SETTER(header_checksum_errors)
  MR60BHA2_SENSOR_SETTER(data_checksum_errors)
  MR60BHA2_SENSOR_SETTER(oversize_frame_errors)
  MR60BHA2_SENSOR_SETTER(unknown_frame_count)
  MR60BHA2_SENSOR_SETTER(last_frame_id)
  MR60BHA2_SENSOR_SETTER(last_frame_type)
  MR60BHA2_SENSOR_SETTER(last_unknown_type)

#undef MR60BHA2_SENSOR_SETTER

#define MR60BHA2_INDEXED_SENSOR_SETTER(group, field)                                    \
  void set_##group##_##field##_sensor(uint8_t index, sensor::Sensor *sensor) {           \
    if (index < MR60BHA2_MAX_TARGETS)                                                     \
      this->group##_##field##_sensors_[index] = sensor;                                  \
  }

  MR60BHA2_INDEXED_SENSOR_SETTER(target, x)
  MR60BHA2_INDEXED_SENSOR_SETTER(target, y)
  MR60BHA2_INDEXED_SENSOR_SETTER(target, doppler_index)
  MR60BHA2_INDEXED_SENSOR_SETTER(target, speed)
  MR60BHA2_INDEXED_SENSOR_SETTER(target, distance)
  MR60BHA2_INDEXED_SENSOR_SETTER(target, angle)
  MR60BHA2_INDEXED_SENSOR_SETTER(target, cluster_id)

  MR60BHA2_INDEXED_SENSOR_SETTER(point, x)
  MR60BHA2_INDEXED_SENSOR_SETTER(point, y)
  MR60BHA2_INDEXED_SENSOR_SETTER(point, doppler_index)
  MR60BHA2_INDEXED_SENSOR_SETTER(point, speed)
  MR60BHA2_INDEXED_SENSOR_SETTER(point, distance)
  MR60BHA2_INDEXED_SENSOR_SETTER(point, angle)
  MR60BHA2_INDEXED_SENSOR_SETTER(point, cluster_id)

#undef MR60BHA2_INDEXED_SENSOR_SETTER
#endif

#ifdef USE_TEXT_SENSOR
  void set_firmware_version_text_sensor(text_sensor::TextSensor *sensor) {
    this->firmware_version_text_sensor_ = sensor;
  }
  void set_debug_log_text_sensor(text_sensor::TextSensor *sensor) { this->debug_log_text_sensor_ = sensor; }
  void set_last_unknown_frame_text_sensor(text_sensor::TextSensor *sensor) {
    this->last_unknown_frame_text_sensor_ = sensor;
  }
#endif

 protected:
  void feed_byte_(uint8_t byte);
  void reset_parser_();
  void process_frame_(uint16_t frame_id, uint16_t frame_type, const uint8_t *data, size_t length);
  void process_targets_(const uint8_t *data, size_t length, bool point_cloud);
  void publish_target_(uint8_t index, float x, float y, int32_t doppler_index, int32_t cluster_id,
                       bool point_cloud);
  void clear_targets_from_(uint8_t start_index, bool point_cloud);
  void publish_diagnostics_(uint32_t now);
  void request_firmware_info_();

  static uint8_t calculate_checksum_(const uint8_t *data, size_t length);
  static uint16_t read_u16_be_(const uint8_t *data);
  static uint16_t read_u16_le_(const uint8_t *data);
  static uint32_t read_u32_le_(const uint8_t *data);
  static int32_t read_i32_le_(const uint8_t *data);
  static float read_float_le_(const uint8_t *data);
  static std::string hex_preview_(uint16_t frame_type, const uint8_t *data, size_t length);

  std::vector<uint8_t> frame_buffer_;
  size_t expected_frame_size_{0};

  uint32_t last_stats_ms_{0};
  uint32_t last_valid_packet_ms_{0};
  uint32_t last_phase_packet_ms_{0};
  uint32_t last_target_packet_ms_{0};
  uint32_t last_point_cloud_packet_ms_{0};

  uint32_t frames_in_window_{0};
  uint32_t phase_frames_in_window_{0};
  uint32_t target_frames_in_window_{0};
  uint32_t point_cloud_frames_in_window_{0};

  uint32_t valid_frame_count_{0};
  uint32_t header_checksum_errors_{0};
  uint32_t data_checksum_errors_{0};
  uint32_t oversize_frame_errors_{0};
  uint32_t unknown_frame_count_{0};

  uint16_t last_frame_id_{0};
  uint16_t last_frame_type_{0};
  uint16_t last_unknown_type_{0};

  uint8_t previous_target_count_{0};
  uint8_t previous_point_cloud_count_{0};

  bool firmware_request_sent_{false};
  uint16_t outbound_frame_id_{0x8000};
  bool last_vital_signs_valid_{false};

#ifdef USE_BINARY_SENSOR
  binary_sensor::BinarySensor *has_target_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *radar_data_valid_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *vital_signs_valid_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *phase_data_valid_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *target_data_valid_binary_sensor_{nullptr};
  binary_sensor::BinarySensor *point_cloud_data_valid_binary_sensor_{nullptr};
#endif

#ifdef USE_SENSOR
#define MR60BHA2_SENSOR_POINTER(name) sensor::Sensor *name##_sensor_{nullptr};
  MR60BHA2_SENSOR_POINTER(breath_rate)
  MR60BHA2_SENSOR_POINTER(heart_rate)
  MR60BHA2_SENSOR_POINTER(distance)
  MR60BHA2_SENSOR_POINTER(num_targets)
  MR60BHA2_SENSOR_POINTER(total_phase)
  MR60BHA2_SENSOR_POINTER(breath_phase)
  MR60BHA2_SENSOR_POINTER(heart_phase)
  MR60BHA2_SENSOR_POINTER(range_flag)
  MR60BHA2_SENSOR_POINTER(point_cloud_count)
  MR60BHA2_SENSOR_POINTER(alternative_x)
  MR60BHA2_SENSOR_POINTER(alternative_y)
  MR60BHA2_SENSOR_POINTER(status_code)
  MR60BHA2_SENSOR_POINTER(firmware_project)
  MR60BHA2_SENSOR_POINTER(firmware_major)
  MR60BHA2_SENSOR_POINTER(firmware_sub)
  MR60BHA2_SENSOR_POINTER(firmware_modified)
  MR60BHA2_SENSOR_POINTER(packet_rate)
  MR60BHA2_SENSOR_POINTER(phase_packet_rate)
  MR60BHA2_SENSOR_POINTER(target_packet_rate)
  MR60BHA2_SENSOR_POINTER(point_cloud_packet_rate)
  MR60BHA2_SENSOR_POINTER(last_packet_age)
  MR60BHA2_SENSOR_POINTER(last_phase_age)
  MR60BHA2_SENSOR_POINTER(last_target_age)
  MR60BHA2_SENSOR_POINTER(last_point_cloud_age)
  MR60BHA2_SENSOR_POINTER(valid_frame_count)
  MR60BHA2_SENSOR_POINTER(header_checksum_errors)
  MR60BHA2_SENSOR_POINTER(data_checksum_errors)
  MR60BHA2_SENSOR_POINTER(oversize_frame_errors)
  MR60BHA2_SENSOR_POINTER(unknown_frame_count)
  MR60BHA2_SENSOR_POINTER(last_frame_id)
  MR60BHA2_SENSOR_POINTER(last_frame_type)
  MR60BHA2_SENSOR_POINTER(last_unknown_type)
#undef MR60BHA2_SENSOR_POINTER

  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> target_x_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> target_y_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> target_doppler_index_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> target_speed_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> target_distance_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> target_angle_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> target_cluster_id_sensors_{};

  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> point_x_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> point_y_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> point_doppler_index_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> point_speed_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> point_distance_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> point_angle_sensors_{};
  std::array<sensor::Sensor *, MR60BHA2_MAX_TARGETS> point_cluster_id_sensors_{};
#endif

#ifdef USE_TEXT_SENSOR
  text_sensor::TextSensor *firmware_version_text_sensor_{nullptr};
  text_sensor::TextSensor *debug_log_text_sensor_{nullptr};
  text_sensor::TextSensor *last_unknown_frame_text_sensor_{nullptr};
  std::string last_debug_log_;
#endif
};

}  // namespace esphome::seeed_mr60bha2
