# OpenVINO™ Telemetry

A Python 3 library used by OpenVINO™ toolkit components to send anonymous usage telemetry to Google Analytics, subject to the user's consent.

## Installation

```sh
pip install openvino-telemetry
```

The package has no third-party dependencies. It installs the `openvino_telemetry` Python module and the `opt_in_out` console script.

## Usage

```python
import openvino_telemetry as tm

# The first instantiation configures the singleton.
telemetry = tm.Telemetry(app_name="my_tool", app_version="1.0", tid="G-XXXXXXXXXX", backend="ga4")

telemetry.start_session("my_tool")
telemetry.send_event("my_tool", "framework", "onnx")
telemetry.send_error("my_tool", "error_code_123")
telemetry.end_session("my_tool")

# Stop sending threads that may hang, e.g. when there is no Internet connection.
telemetry.force_shutdown(1.0)
```

`Telemetry` is a singleton. The first instantiation must provide `app_name`, `app_version` and `tid`; later calls to `tm.Telemetry()` without arguments return the already configured instance (a `RuntimeError` is raised if it was never configured).

### Constructor parameters

| Parameter | Default | Description |
|---|---|---|
| `app_name` | `None` | Name of the application. Required on first instantiation. |
| `app_version` | `None` | Version of the application. |
| `tid` | `None` | GA base ID. If not set, a warning is logged and data is not delivered. |
| `backend` | `'ga'` | Telemetry backend: `'ga4'` (Google Analytics 4, recommended) or `'ga'` (legacy Universal Analytics). |
| `disable_in_ci` | `False` | If `True`, telemetry is disabled when a CI environment is detected (`CI=true`, `TF_BUILD` or `JENKINS_URL` is set). |

### API

| Method | Description |
|---|---|
| `send_event(category, action, label, value=1, app_name=None, app_version=None, force_send=False)` | Sends a single event. `app_name`/`app_version` override the configured values for this event. |
| `start_session(category)` | Sends a session start event. For `ga4` a new session ID is generated. |
| `end_session(category)` | Sends a session end event. |
| `send_error(category, error_msg)` | Sends an error event. |
| `send_stack_trace(category, stack_trace)` | Sends a stack trace event. |
| `force_shutdown(timeout=1.0)` | Waits up to `timeout` seconds if messages are still queued, then stops sending threads. |
| `Telemetry.opt_in(tid)` / `Telemetry.opt_out(tid)` | Programmatically change the consent status (same as the `opt_in_out` script). |

Messages are sent asynchronously in a thread pool. At most 1000 messages may be queued; further messages are dropped. With the `ga4` backend on Linux and macOS each request runs in a separate process that is terminated after 3 seconds. All network errors are silently ignored.

### Event conventions

To send the data, use three variables: `category`, `action`, and `label`.

- In the `category`, use only the name of the tool, for example `ovc`.
- In the `action`, send a metric or a function, such as accuracy, session, conversion, and others. With the `ga4` backend the action becomes the GA4 event name.
- In the `label`, send more detailed data for your action (function). For example, send a string with the version name for the version or a string with the framework name for the framework. You can send a string with a wrapped dictionary: "{param: value, version: value, error: value}".

With the `ga4` backend every event additionally contains the following parameters: `app_name`, `app_version`, `os`, `docker` (whether the process runs in a Docker container), `session_id`, `usage_count` and `usage_group`.

## Consent

Telemetry is sent by default unless the user explicitly declines it using the `opt_in_out` script or `OPENVINO_TELEMETRY_OPTOUT=1` environment variable. The consent status is stored in the `openvino_telemetry` file:

| OS | Location |
|---|---|
| Linux, macOS | `~/intel/openvino_telemetry` |
| Windows | `%LOCALAPPDATA%\Intel Corporation\openvino_telemetry` |

The file contains `1` if the user accepted and `0` if the user declined. Any other content is treated as declined.

If the consent file exists, its value is used. If it does not exist, telemetry is sent, as long as the consent directory is writable (so that the user is able to opt out). If the directory is not writable, no telemetry is sent.

### Opting in or out

Use the `opt_in_out` script installed with the package:

```sh
opt_in_out --opt_in
opt_in_out --opt_out
```

Opting out writes `0` to the consent file and removes the client ID and statistics files.

To disable telemetry regardless of the consent file, set the environment variable:

```sh
export OPENVINO_TELEMETRY_OPTOUT=1
```

In this case no data is sent and nothing is written to the local machine, and `opt_in_out` does not modify the consent file.

## Local files

All files are stored in the same directory as the consent file:

- `openvino_telemetry` - consent status.
- `openvino_ga_cid` - randomly generated anonymous client ID (UUID4). It is created only when telemetry is enabled. A legacy `openvino_ga_uid` file is migrated by the `ga4` backend.
- `stats` - JSON file with the `usage_count` counter, updated on each `Telemetry` initialization when telemetry is enabled.

## Development

Build a wheel:

```sh
python setup.py sdist bdist_wheel
```

Run tests from the repository root:

```sh
pytest src
```
