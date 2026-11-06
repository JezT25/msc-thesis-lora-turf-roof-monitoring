# Design and Implementation of a Low-Power LoRa Wireless Sensor Mesh Network with Cloud Storage for Monitoring Soil Conditions on Icelandic Turf Roofs

M.Sc. thesis in Electrical and Computer Engineering, University of Iceland (60 ECTS)

**Author:** Jezreel V. Tan
**Supervisors:** Helgi Þorbergsson, Ph.D.; Dórótea Höeg Sigurðardóttir
**Faculty:** Electrical and Computer Engineering, School of Engineering and Natural Sciences, University of Iceland
**Expected submission:** February 2027

## Abstract

This thesis presents the design, implementation, and evaluation of a low-cost, low-power wireless sensor network for monitoring soil and environmental conditions beneath Icelandic turf roofs. Sensor nodes are concealed under the turf, communicate over 433 MHz LoRa, and forward measurements to a base station that uploads them to the ThingSpeak cloud platform for remote access. The system was evaluated through laboratory power measurements, field range tests, sensor calibration, cloud-upload tests, and a long-term deployment at the Keldur turf-house site in cooperation with the National Museum of Iceland.

## System Overview

| Component | Description |
| --- | --- |
| Sensor node | Arduino Pro Mini (ATmega328P), Ra-02 (SX1278) 433 MHz LoRa module, DS3231 real-time clock, SD-card storage |
| Sensors | Capacitive soil moisture, DS18B20 soil temperature, AHT10 air temperature and relative humidity, battery voltage |
| Base station | LOLIN D1 mini (ESP8266) with Ra-02 LoRa module and Wi-Fi uplink |
| Networking | LoRa mesh with relay functionality; packets obfuscated with a lightweight RC4 routine |
| Cloud | ThingSpeak (HTTP) |
| Firmware | Arduino IDE; sensor node and base station firmware in [JezT25/turfroof_lora](https://github.com/JezT25/turfroof_lora) |
| Hardware | Custom PCB design |

## Key Results

| Area | Result |
| --- | --- |
| Power consumption | Weighted average current of approximately 3.08 mA under the defined operating cycle |
| Estimated battery life | Approximately 142 days with 3 × 3,500 mAh cells in parallel (10,500 mAh nominal); idealized estimate that excludes low-temperature capacity loss |
| LoRa range (Vellir, Hafnarfjörður) | Successful single-hop communication at several locations within approximately 3 km; RSSI from −103 dBm to −113 dBm; occasional packet loss in obstructed areas |
| Soil moisture calibration | Second-order polynomial over the 0–40 % gravimetric range; in-sample RMSE of approximately 3.01 percentage points |
| Cloud upload | HTTP 200 OK responses; average upload time of approximately 1–2 seconds |
| Keldur deployment | Four nodes beneath four turf roofs; first-to-last valid record spans of approximately 51 to 130 days |

Mesh relay behavior was observed qualitatively on the bench; no multi-hop range is reported.

## Research Objectives

1. Implement distributed sensor nodes for soil moisture, soil temperature, air temperature, relative humidity, and battery voltage.
2. Implement LoRa communication and evaluate range and field operation.
3. Measure node current consumption and estimate battery life.
4. Implement and evaluate local data storage.
5. Develop and evaluate a calibration model for the capacitive soil moisture sensor.
6. Integrate the network with a cloud platform and evaluate upload behavior.

## Repository Structure

```text
.
├── main.tex            Main document: metadata, front matter, chapter inclusion, conclusion
├── references.bib      Bibliography (BibLaTeX/Biber)
├── chapters/
│   ├── 01_introduction.tex
│   ├── 02_rrl.tex      Review of related literature
│   ├── 03_methodology.tex
│   └── 04_results.tex
├── appendix/           Bill of Materials
└── figs/               Figures, photographs, and the University of Iceland banner
```

## Firmware

The sensor node and base station firmware used in this thesis is available at [github.com/JezT25/turfroof_lora](https://github.com/JezT25/turfroof_lora).

## Data

Measurements from the Keldur deployment are published on ThingSpeak (channel author: `jvt6hiis`), one channel per sensor node.

| Node | Channel |
| --- | --- |
| HW_1 | [2974951](https://thingspeak.mathworks.com/channels/2974951) |
| HW_3 | [2974954](https://thingspeak.mathworks.com/channels/2974954) |
| HW_5 | [2974955](https://thingspeak.mathworks.com/channels/2974955) |
| HW_7 | [2974956](https://thingspeak.mathworks.com/channels/2974956) |

## Copyright

Copyright © 2027 Jezreel V. Tan. This thesis may not be copied in any form without the author's permission.
