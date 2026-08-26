#include "seeed_mr60bha2.h"

#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <limits>

namespace esphome::seeed_mr60bha2 {

static const char *const TAG = "seeed_mr60bha2.extended";
static constexpr float MR60BHA2_DOPPLER_TO_METERS_PER_SECOND = 0.1728f;
static constexpr float MR60BHA2_RADIANS_TO_DEGREES = 57.29577951308232f;
static constexpr uint32_t MR60BHA2_VALIDITY_TIMEOUT_MS = 2500;

#ifdef USE_SENSOR
static void publish_sensor(sensor::Sensor *sensor, float value) {
  if (sensor != nullptr)
    sensor->publish_state(value);
}
#endif

#ifdef USE_BINARY_SENSOR
static void publish_binary(binary_sensor::BinarySensor *sensor, bool value) {
  if (sensor != nullptr)
    sensor->publish_state(value);
}
#endif

void MR60BHA2Component::setup() {
  this->frame_buffer_.reserve(96);
  this->last_stats_ms_ = millis();
}

void MR60BHA2Component::dump_config() {
  ESP_LOGCONFIG(TAG, "MR60BHA2 Extended:");
#ifdef USE_BINARY_SENSOR
  LOG_BINARY_SENSOR("  ", "Presence", this->has_target_binary_sensor_);
  LOG_BINARY_SENSOR("  ", "Radar Data Valid", this->radar_data_valid_binary_sensor_);
  LOG_BINARY_SENSOR("  ", "Vital Signs Valid", this->vital_signs_valid_binary_sensor_);
  LOG_BINARY_SENSOR("  ", "Phase Data Valid", this->phase_data_valid_binary_sensor_);
  LOG_BINARY_SENSOR("  ", "Target Data Valid", this->target_data_valid_binary_sensor_);
  LOG_BINARY_SENSOR("  ", "Point Cloud Data Valid", this->point_cloud_data_valid_binary_sensor_);
#endif
#ifdef USE_SENSOR
  LOG_SENSOR("  ", "Breath Rate", this->breath_rate_sensor_);
  LOG_SENSOR("  ", "Heart Rate", this->heart_rate_sensor_);
  LOG_SENSOR("  ", "Distance", this->distance_sensor_);
  LOG_SENSOR("  ", "Target Count", this->num_targets_sensor_);
  LOG_SENSOR("  ", "Total Phase", this->total_phase_sensor_);
  LOG_SENSOR("  ", "Breath Phase", this->breath_phase_sensor_);
  LOG_SENSOR("  ", "Heart Phase", this->heart_phase_sensor_);
  LOG_SENSOR("  ", "Point Cloud Count", this->point_cloud_count_sensor_);
#endif
#ifdef USE_TEXT_SENSOR
  LOG_TEXT_SENSOR("  ", "Firmware Version", this->firmware_version_text_sensor_);
  LOG_TEXT_SENSOR("  ", "Debug Log", this->debug_log_text_sensor_);
  LOG_TEXT_SENSOR("  ", "Last Unknown Frame", this->last_unknown_frame_text_sensor_);
#endif
}

void MR60BHA2Component::loop() {
  size_t available_bytes = this->available();
  uint8_t read_buffer[64];

  while (available_bytes > 0) {
    const size_t bytes_to_read = std::min(available_bytes, sizeof(read_buffer));
    if (!this->read_array(read_buffer, bytes_to_read))
      break;

    for (size_t i = 0; i < bytes_to_read; i++)
      this->feed_byte_(read_buffer[i]);

    available_bytes -= bytes_to_read;
  }

  const uint32_t now = millis();

  if (!this->firmware_request_sent_ && now > 5000) {
    this->request_firmware_info_();
    this->firmware_request_sent_ = true;
  }

  if (now - this->last_stats_ms_ >= 1000)
    this->publish_diagnostics_(now);
}

void MR60BHA2Component::feed_byte_(uint8_t byte) {
  if (this->frame_buffer_.empty()) {
    if (byte == MR60BHA2_FRAME_START)
      this->frame_buffer_.push_back(byte);
    return;
  }

  this->frame_buffer_.push_back(byte);

  if (this->frame_buffer_.size() == MR60BHA2_HEADER_SIZE) {
    if (calculate_checksum_(this->frame_buffer_.data(), 7) != this->frame_buffer_[7]) {
      this->header_checksum_errors_++;
      ESP_LOGV(TAG, "Header checksum failure");
      this->reset_parser_();
      return;
    }

    const uint16_t payload_length = read_u16_be_(&this->frame_buffer_[3]);
    if (payload_length > MR60BHA2_MAX_PAYLOAD_SIZE) {
      this->oversize_frame_errors_++;
      ESP_LOGW(TAG, "Rejected oversized frame payload: %u bytes", payload_length);
      this->reset_parser_();
      return;
    }

    this->expected_frame_size_ = MR60BHA2_HEADER_SIZE + payload_length + 1;
  }

  if (this->expected_frame_size_ == 0 || this->frame_buffer_.size() < this->expected_frame_size_)
    return;

  if (this->frame_buffer_.size() > this->expected_frame_size_) {
    this->reset_parser_();
    return;
  }

  const size_t payload_length = this->expected_frame_size_ - MR60BHA2_HEADER_SIZE - 1;
  const uint8_t expected_checksum = this->frame_buffer_.back();
  const uint8_t calculated_checksum = calculate_checksum_(&this->frame_buffer_[MR60BHA2_HEADER_SIZE], payload_length);

  if (calculated_checksum != expected_checksum) {
    this->data_checksum_errors_++;
    ESP_LOGV(TAG, "Data checksum failure");
    this->reset_parser_();
    return;
  }

  const uint16_t frame_id = read_u16_be_(&this->frame_buffer_[1]);
  const uint16_t frame_type = read_u16_be_(&this->frame_buffer_[5]);
  const uint8_t *payload = &this->frame_buffer_[MR60BHA2_HEADER_SIZE];

  this->valid_frame_count_++;
  this->frames_in_window_++;
  this->last_frame_id_ = frame_id;
  this->last_frame_type_ = frame_type;
  this->last_valid_packet_ms_ = millis();

  this->process_frame_(frame_id, frame_type, payload, payload_length);
  this->reset_parser_();
}

void MR60BHA2Component::reset_parser_() {
  this->frame_buffer_.clear();
  this->expected_frame_size_ = 0;
}

void MR60BHA2Component::process_frame_(uint16_t frame_id, uint16_t frame_type, const uint8_t *data,
                                      size_t length) {
  (void) frame_id;
  const uint32_t now = millis();

  switch (frame_type) {
    case MR60BHA2_TYPE_PHASE:
      if (length >= 12) {
#ifdef USE_SENSOR
        publish_sensor(this->total_phase_sensor_, read_float_le_(data));
        publish_sensor(this->breath_phase_sensor_, read_float_le_(data + 4));
        publish_sensor(this->heart_phase_sensor_, read_float_le_(data + 8));
#endif
        this->phase_frames_in_window_++;
        this->last_phase_packet_ms_ = now;
      }
      break;

    case MR60BHA2_TYPE_BREATH_RATE:
      if (length >= 4) {
#ifdef USE_SENSOR
        publish_sensor(this->breath_rate_sensor_, read_float_le_(data));
#endif
      }
      break;

    case MR60BHA2_TYPE_HEART_RATE:
      if (length >= 4) {
#ifdef USE_SENSOR
        publish_sensor(this->heart_rate_sensor_, read_float_le_(data));
#endif
      }
      break;

    case MR60BHA2_TYPE_DISTANCE:
      if (length >= 8) {
        const uint32_t range_flag = read_u32_le_(data);
        const float distance = read_float_le_(data + 4);
        this->last_vital_signs_valid_ = range_flag != 0;
#ifdef USE_SENSOR
        publish_sensor(this->range_flag_sensor_, static_cast<float>(range_flag));
        publish_sensor(this->distance_sensor_, range_flag != 0 ? distance : 0.0f);
#endif
#ifdef USE_BINARY_SENSOR
        publish_binary(this->vital_signs_valid_binary_sensor_, this->last_vital_signs_valid_);
#endif
      }
      break;

    case MR60BHA2_TYPE_HUMAN_DETECTION:
      if (length >= 1) {
        const bool detected = length >= 4 ? read_u32_le_(data) != 0 : data[0] != 0;
#ifdef USE_BINARY_SENSOR
        publish_binary(this->has_target_binary_sensor_, detected);
#endif
        if (!detected) {
#ifdef USE_SENSOR
          publish_sensor(this->breath_rate_sensor_, 0.0f);
          publish_sensor(this->heart_rate_sensor_, 0.0f);
          publish_sensor(this->distance_sensor_, 0.0f);
          publish_sensor(this->num_targets_sensor_, 0.0f);
#endif
          this->clear_targets_from_(0, false);
          this->previous_target_count_ = 0;
        }
      }
      break;

    case MR60BHA2_TYPE_TARGET_INFO:
      this->target_frames_in_window_++;
      this->last_target_packet_ms_ = now;
      this->process_targets_(data, length, false);
      break;

    case MR60BHA2_TYPE_POINT_CLOUD:
      this->point_cloud_frames_in_window_++;
      this->last_point_cloud_packet_ms_ = now;
      this->process_targets_(data, length, true);
      break;

    case MR60BHA2_TYPE_ALTERNATIVE_POSITION:
      if (length >= 8) {
#ifdef USE_SENSOR
        publish_sensor(this->alternative_x_sensor_, read_float_le_(data));
        publish_sensor(this->alternative_y_sensor_, read_float_le_(data + 4));
#endif
      }
      break;

    case MR60BHA2_TYPE_STATUS_CODE:
      if (length >= 2) {
#ifdef USE_SENSOR
        publish_sensor(this->status_code_sensor_, static_cast<float>(read_u16_le_(data)));
#endif
      }
      break;

    case MR60BHA2_TYPE_FIRMWARE:
      if (length >= 4) {
        uint32_t project = 0;
        uint32_t major = 0;
        uint32_t sub = 0;
        uint32_t modified = 0;

        if (length >= 12) {
          project = read_u32_le_(data);
          major = read_u32_le_(data + 4);
          sub = read_u16_le_(data + 8);
          modified = read_u16_le_(data + 10);
        } else {
          project = data[0];
          major = data[1];
          sub = data[2];
          modified = data[3];
        }

#ifdef USE_SENSOR
        publish_sensor(this->firmware_project_sensor_, static_cast<float>(project));
        publish_sensor(this->firmware_major_sensor_, static_cast<float>(major));
        publish_sensor(this->firmware_sub_sensor_, static_cast<float>(sub));
        publish_sensor(this->firmware_modified_sensor_, static_cast<float>(modified));
#endif
#ifdef USE_TEXT_SENSOR
        if (this->firmware_version_text_sensor_ != nullptr) {
          char version[48];
          snprintf(version, sizeof(version), "project %lu, v%lu.%lu.%lu", static_cast<unsigned long>(project),
                   static_cast<unsigned long>(major), static_cast<unsigned long>(sub),
                   static_cast<unsigned long>(modified));
          this->firmware_version_text_sensor_->publish_state(version);
        }
#endif
      }
      break;

    case MR60BHA2_TYPE_DEBUG_LOG:
#ifdef USE_TEXT_SENSOR
      if (this->debug_log_text_sensor_ != nullptr && length > 0) {
        std::string message(reinterpret_cast<const char *>(data), length);
        const size_t null_pos = message.find('\0');
        if (null_pos != std::string::npos)
          message.resize(null_pos);
        while (!message.empty() && (message.back() == ' ' || message.back() == '\r' || message.back() == '\n'))
          message.pop_back();
        if (!message.empty() && message != this->last_debug_log_) {
          this->last_debug_log_ = message;
          this->debug_log_text_sensor_->publish_state(message);
        }
      }
#endif
      break;

    default:
      this->unknown_frame_count_++;
      this->last_unknown_type_ = frame_type;
#ifdef USE_TEXT_SENSOR
      if (this->last_unknown_frame_text_sensor_ != nullptr)
        this->last_unknown_frame_text_sensor_->publish_state(hex_preview_(frame_type, data, length));
#endif
      ESP_LOGV(TAG, "Unknown frame type 0x%04X, length=%u", frame_type, static_cast<unsigned>(length));
      break;
  }
}

void MR60BHA2Component::process_targets_(const uint8_t *data, size_t length, bool point_cloud) {
  if (length < 4)
    return;

  const uint32_t reported_count = read_u32_le_(data);
  const uint8_t count = static_cast<uint8_t>(std::min<uint32_t>(reported_count, MR60BHA2_MAX_TARGETS));
  const size_t required_length = 4 + static_cast<size_t>(count) * 16;

  if (length < required_length)
    return;

#ifdef USE_SENSOR
  if (point_cloud)
    publish_sensor(this->point_cloud_count_sensor_, static_cast<float>(reported_count));
  else
    publish_sensor(this->num_targets_sensor_, static_cast<float>(reported_count));
#endif

  const uint8_t *cursor = data + 4;
  for (uint8_t index = 0; index < count; index++) {
    const float x = read_float_le_(cursor);
    const float y = read_float_le_(cursor + 4);
    const int32_t doppler_index = read_i32_le_(cursor + 8);
    const int32_t cluster_id = read_i32_le_(cursor + 12);
    this->publish_target_(index, x, y, doppler_index, cluster_id, point_cloud);
    cursor += 16;
  }

  this->clear_targets_from_(count, point_cloud);
  if (point_cloud)
    this->previous_point_cloud_count_ = count;
  else
    this->previous_target_count_ = count;
}

void MR60BHA2Component::publish_target_(uint8_t index, float x, float y, int32_t doppler_index,
                                       int32_t cluster_id, bool point_cloud) {
  if (index >= MR60BHA2_MAX_TARGETS)
    return;

#ifdef USE_SENSOR
  const float speed = static_cast<float>(doppler_index) * MR60BHA2_DOPPLER_TO_METERS_PER_SECOND;
  const float distance = std::sqrt(x * x + y * y);
  const float angle = std::atan2(x, y) * MR60BHA2_RADIANS_TO_DEGREES;

  auto &x_sensors = point_cloud ? this->point_x_sensors_ : this->target_x_sensors_;
  auto &y_sensors = point_cloud ? this->point_y_sensors_ : this->target_y_sensors_;
  auto &doppler_sensors = point_cloud ? this->point_doppler_index_sensors_ : this->target_doppler_index_sensors_;
  auto &speed_sensors = point_cloud ? this->point_speed_sensors_ : this->target_speed_sensors_;
  auto &distance_sensors = point_cloud ? this->point_distance_sensors_ : this->target_distance_sensors_;
  auto &angle_sensors = point_cloud ? this->point_angle_sensors_ : this->target_angle_sensors_;
  auto &cluster_sensors = point_cloud ? this->point_cluster_id_sensors_ : this->target_cluster_id_sensors_;

  publish_sensor(x_sensors[index], x);
  publish_sensor(y_sensors[index], y);
  publish_sensor(doppler_sensors[index], static_cast<float>(doppler_index));
  publish_sensor(speed_sensors[index], speed);
  publish_sensor(distance_sensors[index], distance);
  publish_sensor(angle_sensors[index], angle);
  publish_sensor(cluster_sensors[index], static_cast<float>(cluster_id));
#endif
}

void MR60BHA2Component::clear_targets_from_(uint8_t start_index, bool point_cloud) {
#ifdef USE_SENSOR
  const float unavailable = std::numeric_limits<float>::quiet_NaN();
  auto &x_sensors = point_cloud ? this->point_x_sensors_ : this->target_x_sensors_;
  auto &y_sensors = point_cloud ? this->point_y_sensors_ : this->target_y_sensors_;
  auto &doppler_sensors = point_cloud ? this->point_doppler_index_sensors_ : this->target_doppler_index_sensors_;
  auto &speed_sensors = point_cloud ? this->point_speed_sensors_ : this->target_speed_sensors_;
  auto &distance_sensors = point_cloud ? this->point_distance_sensors_ : this->target_distance_sensors_;
  auto &angle_sensors = point_cloud ? this->point_angle_sensors_ : this->target_angle_sensors_;
  auto &cluster_sensors = point_cloud ? this->point_cluster_id_sensors_ : this->target_cluster_id_sensors_;

  const uint8_t previous_count = point_cloud ? this->previous_point_cloud_count_ : this->previous_target_count_;
  const uint8_t clear_until = std::min<uint8_t>(previous_count, MR60BHA2_MAX_TARGETS);

  for (uint8_t index = start_index; index < clear_until; index++) {
    publish_sensor(x_sensors[index], unavailable);
    publish_sensor(y_sensors[index], unavailable);
    publish_sensor(doppler_sensors[index], unavailable);
    publish_sensor(speed_sensors[index], unavailable);
    publish_sensor(distance_sensors[index], unavailable);
    publish_sensor(angle_sensors[index], unavailable);
    publish_sensor(cluster_sensors[index], unavailable);
  }
#else
  (void) start_index;
  (void) point_cloud;
#endif
}

void MR60BHA2Component::publish_diagnostics_(uint32_t now) {
  const uint32_t elapsed = now - this->last_stats_ms_;
  if (elapsed == 0)
    return;

  const float scale = 1000.0f / static_cast<float>(elapsed);
  const bool radar_valid = this->last_valid_packet_ms_ != 0 && now - this->last_valid_packet_ms_ <= MR60BHA2_VALIDITY_TIMEOUT_MS;
  const bool phase_valid = this->last_phase_packet_ms_ != 0 && now - this->last_phase_packet_ms_ <= MR60BHA2_VALIDITY_TIMEOUT_MS;
  const bool target_valid = this->last_target_packet_ms_ != 0 && now - this->last_target_packet_ms_ <= MR60BHA2_VALIDITY_TIMEOUT_MS;
  const bool point_valid = this->last_point_cloud_packet_ms_ != 0 && now - this->last_point_cloud_packet_ms_ <= MR60BHA2_VALIDITY_TIMEOUT_MS;

#ifdef USE_BINARY_SENSOR
  publish_binary(this->radar_data_valid_binary_sensor_, radar_valid);
  publish_binary(this->phase_data_valid_binary_sensor_, phase_valid);
  publish_binary(this->target_data_valid_binary_sensor_, target_valid);
  publish_binary(this->point_cloud_data_valid_binary_sensor_, point_valid);
#endif

#ifdef USE_SENSOR
  publish_sensor(this->packet_rate_sensor_, static_cast<float>(this->frames_in_window_) * scale);
  publish_sensor(this->phase_packet_rate_sensor_, static_cast<float>(this->phase_frames_in_window_) * scale);
  publish_sensor(this->target_packet_rate_sensor_, static_cast<float>(this->target_frames_in_window_) * scale);
  publish_sensor(this->point_cloud_packet_rate_sensor_, static_cast<float>(this->point_cloud_frames_in_window_) * scale);

  const float unavailable = std::numeric_limits<float>::quiet_NaN();
  publish_sensor(this->last_packet_age_sensor_, this->last_valid_packet_ms_ == 0
                                                   ? unavailable
                                                   : static_cast<float>(now - this->last_valid_packet_ms_) / 1000.0f);
  publish_sensor(this->last_phase_age_sensor_, this->last_phase_packet_ms_ == 0
                                                  ? unavailable
                                                  : static_cast<float>(now - this->last_phase_packet_ms_) / 1000.0f);
  publish_sensor(this->last_target_age_sensor_, this->last_target_packet_ms_ == 0
                                                   ? unavailable
                                                   : static_cast<float>(now - this->last_target_packet_ms_) / 1000.0f);
  publish_sensor(this->last_point_cloud_age_sensor_, this->last_point_cloud_packet_ms_ == 0
                                                        ? unavailable
                                                        : static_cast<float>(now - this->last_point_cloud_packet_ms_) / 1000.0f);

  publish_sensor(this->valid_frame_count_sensor_, static_cast<float>(this->valid_frame_count_));
  publish_sensor(this->header_checksum_errors_sensor_, static_cast<float>(this->header_checksum_errors_));
  publish_sensor(this->data_checksum_errors_sensor_, static_cast<float>(this->data_checksum_errors_));
  publish_sensor(this->oversize_frame_errors_sensor_, static_cast<float>(this->oversize_frame_errors_));
  publish_sensor(this->unknown_frame_count_sensor_, static_cast<float>(this->unknown_frame_count_));
  publish_sensor(this->last_frame_id_sensor_, static_cast<float>(this->last_frame_id_));
  publish_sensor(this->last_frame_type_sensor_, static_cast<float>(this->last_frame_type_));
  publish_sensor(this->last_unknown_type_sensor_, static_cast<float>(this->last_unknown_type_));
#endif

  this->frames_in_window_ = 0;
  this->phase_frames_in_window_ = 0;
  this->target_frames_in_window_ = 0;
  this->point_cloud_frames_in_window_ = 0;
  this->last_stats_ms_ = now;
}

void MR60BHA2Component::request_firmware_info_() {
  uint8_t frame[8];
  frame[0] = MR60BHA2_FRAME_START;
  frame[1] = static_cast<uint8_t>((this->outbound_frame_id_ >> 8) & 0xFF);
  frame[2] = static_cast<uint8_t>(this->outbound_frame_id_ & 0xFF);
  frame[3] = 0x00;
  frame[4] = 0x00;
  frame[5] = 0xFF;
  frame[6] = 0xFF;
  frame[7] = calculate_checksum_(frame, 7);
  this->outbound_frame_id_++;
  this->write_array(frame, sizeof(frame));
  this->flush();
}

uint8_t MR60BHA2Component::calculate_checksum_(const uint8_t *data, size_t length) {
  uint8_t checksum = 0;
  for (size_t i = 0; i < length; i++)
    checksum ^= data[i];
  return static_cast<uint8_t>(~checksum);
}

uint16_t MR60BHA2Component::read_u16_be_(const uint8_t *data) {
  return static_cast<uint16_t>((static_cast<uint16_t>(data[0]) << 8) | data[1]);
}

uint16_t MR60BHA2Component::read_u16_le_(const uint8_t *data) {
  return static_cast<uint16_t>(data[0] | (static_cast<uint16_t>(data[1]) << 8));
}

uint32_t MR60BHA2Component::read_u32_le_(const uint8_t *data) {
  return static_cast<uint32_t>(data[0]) | (static_cast<uint32_t>(data[1]) << 8) |
         (static_cast<uint32_t>(data[2]) << 16) | (static_cast<uint32_t>(data[3]) << 24);
}

int32_t MR60BHA2Component::read_i32_le_(const uint8_t *data) {
  return static_cast<int32_t>(read_u32_le_(data));
}

float MR60BHA2Component::read_float_le_(const uint8_t *data) {
  const uint32_t raw = read_u32_le_(data);
  float value;
  memcpy(&value, &raw, sizeof(value));
  return value;
}

std::string MR60BHA2Component::hex_preview_(uint16_t frame_type, const uint8_t *data, size_t length) {
  char prefix[40];
  snprintf(prefix, sizeof(prefix), "type=0x%04X len=%u data=", frame_type, static_cast<unsigned>(length));
  std::string result(prefix);
  const size_t preview_length = std::min<size_t>(length, 16);
  char byte_text[4];
  for (size_t i = 0; i < preview_length; i++) {
    snprintf(byte_text, sizeof(byte_text), "%02X", data[i]);
    if (i > 0)
      result.push_back(' ');
    result.append(byte_text);
  }
  if (length > preview_length)
    result.append(" …");
  return result;
}

}  // namespace esphome::seeed_mr60bha2
