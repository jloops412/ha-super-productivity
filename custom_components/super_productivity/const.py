"""Constants for the Super Productivity integration."""

DOMAIN = "super_productivity"

CONF_HOST = "host"
CONF_PORT = "port"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3876
DEFAULT_SCAN_INTERVAL = 30  # seconds

# API endpoints
ENDPOINT_HEALTH = "/health"
ENDPOINT_STATUS = "/status"
ENDPOINT_TASKS = "/tasks"
ENDPOINT_TASK_CONTROL_CURRENT = "/task-control/current"
ENDPOINT_TASK_CONTROL_STOP = "/task-control/stop"
ENDPOINT_PROJECTS = "/projects"
ENDPOINT_TAGS = "/tags"

# Special tag IDs
TAG_TODAY = "TODAY"

# Attributes
ATTR_TASK_ID = "task_id"
ATTR_TITLE = "title"
ATTR_PROJECT_ID = "project_id"
ATTR_TAG_IDS = "tag_ids"
ATTR_NOTES = "notes"
ATTR_TIME_ESTIMATE = "time_estimate"
ATTR_TIME_SPENT = "time_spent"
ATTR_IS_DONE = "is_done"
ATTR_DUE_DAY = "due_day"
ATTR_PLANNED_AT = "planned_at"
ATTR_PARENT_ID = "parent_id"
