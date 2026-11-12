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
| Preliminary single-cell tests | SD-card logs show logged operating periods of approximately 11–27 days per node (longest approximately 26.8 days); these are observed durations, not measured full battery lifetimes |
| Keldur deployment | Four nodes beneath four turf roofs; first-to-last valid record spans of approximately 51 to 130 days (not uninterrupted operation or confirmed battery life) |
| Keldur comparison | Comparison with a separate in-situ dataset from the Turf-House Monitoring Project (18 October 2025 – 27 January 2026): daily-mean soil-temperature Pearson correlations of 0.75–0.98; soil-moisture agreement is exploratory and does not establish absolute accuracy |

Mesh relay behavior was observed qualitatively on the bench; no multi-hop range is reported, and the mesh routes used during the Keldur deployment were not quantified because no base-station packet logs were retained.

## Research Objectives

1. Implement distributed sensor nodes for soil moisture, soil temperature, air temperature, relative humidity, and battery voltage.
2. Implement LoRa communication and evaluate range and field operation.
3. Measure node current consumption and estimate battery life.
4. Implement local data storage and evaluate its ability to retain measurements when wireless transmissions are missed.
5. Develop a calibration model for the capacitive soil moisture sensor and evaluate its fit over the tested 0–40 % range.
6. Integrate the network with a cloud platform and evaluate upload behavior.

## Repository Structure

```text
.
├── main.tex            Main document: document class and chapter/front matter inclusion
├── preamble.tex        Packages, thesis metadata, and formatting
├── references.bib      Bibliography (BibLaTeX/Biber)
├── frontmatter/        Title page, abstract, Útdráttur, acknowledgements, abbreviations
├── chapters/
│   ├── 01_introduction.tex
│   ├── 02_rrl.tex      Review of related literature
│   ├── 03_methodology.tex
│   ├── 04_results.tex  Results and discussion, including the Keldur comparison
│   ├── 05_conclusion.tex  Conclusion and recommendations
│   └── A_appendix.tex  Bill of materials and public ThingSpeak channels
├── appendix/           Bill of Materials spreadsheet
├── figs/               Figures, photographs, and the University of Iceland banner
└── testing data/       Raw data exports, logs, and analysis scripts/outputs
    ├── Benchtop Testing (1st Week June)/
    ├── June Testing/
    ├── October Testing/
    └── Keldur Data/    Keldur feeds, reference-station and project data, comparison scripts and plots
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

The public channels are supplementary; the archived data exports in `testing data/` are the basis of the results reported in the thesis.

## Copyright

Copyright © 2027 Jezreel V. Tan. This thesis may not be copied in any form without the author's permission.
