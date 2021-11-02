#  Intel® Distribution of OpenVINO™ Toolkit Telemetry

The implementation of the Python 3 library to send the telemetry data from the OpenVINO™ toolkit components.

To send the data to Google Analytics, use the following three variables: `category`, `action`, and `label`.

- In the `category`, use only the name of the tool. Place all Model Optimizer (MO) topics in the 'mo' category, all Post-Training Optimization Tool (POT) topics in the 'pot' category, and so on. 
- In the `action`, send a metric or a function, such as accuracy, session, conversion, and others. For example, for MO use: version, framework, conversion_results, and so forth.
- In the `label`, send more detailed data for your action (function). For example, send a string with the version name for the version or a string with the framework name for the framework. You can send a string with a wrapped dictionary. For example: "{param: value, version: value, error: value}".

**NOTE:** If you want to track the connection between data (for example, on which operating systems error '123' occurred), send the data in one event and add it to the label together. If you send the data separately, you will not be able to identify the connection. Some data will be duplicated, as the same metric/function will be sent in different events.

**TIP:**  To help automate the analytics, always send **all** the keys for a dictionary in the `label` variable. If a key is empty, send 'none' as its value. 
