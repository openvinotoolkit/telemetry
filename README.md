# Telemetry Library

The implementation of the Python3 library to send telemetry data from OpenVINO™ Toolkit components.

To send any data to Google Analytics you are playing with 3 variables: category, action, label.
- In the category use only the name of the tool. All MO topics should be in 'mo' category, all POT topics in 'pot' category, etc
- In the action send metric or function, like accuracy or session or conversion. For example, for MO we have: version, framework, conversion_results etc
- In the label send more detailed data for your action (function). Ex. for version sent string with version name, for framework send string with framework name etc. In the label you can send a dictionary. Ex. {param: value, version: value, error: value}.
**Note:** if you want to track connection between data, (ex on what OSes error '123' happened), please send it in one event. Suggest adding it to the label together. If you send data separately you cannot find a connection between then. So, it means that some data will be duplicated, as the same metric/function you will send in different events. 

BKM
For ease and automate analytics please follow this rules:
1. If you want to send a dict In label, please always sent **all** keys, even if a key is empty, sent 'none' to it's value. This helps to automate analytics. 