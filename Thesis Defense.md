# Defense Q&A Preparation

**Thesis:** Design and Implementation of a Low-Power LoRa Wireless Sensor Mesh Network with Cloud Storage for Monitoring Soil Conditions on Icelandic Turf Roofs  
**Use:** rehearse aloud. Every answer below is taken from the thesis. Items I derived myself are marked **[my calculation]** and are not in the thesis; verify them before quoting.

**Matching presentation:** [Revised defense deck](Thesis_Defense_Jezreel_Tan_Revised.pptx). For the moisture comparison, use slide 16 and backup B15: **fit early observations, hold the offset fixed, evaluate later observations**.

**Limitation flag:** 🔶 = the honest answer must acknowledge a limitation. ✅ = answer can be given without a caveat.

---

## Numbers to have in your head

| Quantity | Value | Kind of evidence |
|---|---|---|
| Average current | ≈3.08 mA (= 11,079.9 mA·s / 3,600 s) | **Calculated** from measured state currents |
| State currents | 0.3 (deep sleep, 3,300 s) · 9.5 (awake, 3 s) · 119.5 (LoRa RX/TX, 60 s) · 12.2 mA (half sleep, 237 s) | Measured at 4.2 V |
| Battery | 3 × 3,500 mAh in parallel = 10,500 mAh nominal | Nominal |
| Idealized lifetime | ≈142 days (3,409 h); single cell ≈47 days | **Calculated**, no cold derating |
| Single-cell SD logs | 11–27 days; longest 26.8 days (4.136 → 3.560 V) | Observed, not full discharge |
| LoRa settings | 433 MHz, SF10, BW 125 kHz, CR 4/5, 17 dBm, preamble 8, sync 0x12 | Configuration |
| Airtime, 96-byte packet | ≈0.985 s (108 payload symbols, T_sym = 8.192 ms) | Calculated (Semtech equations) |
| Range test | ≈3 km, single-hop, several locations; RSSI −103 to −113 dBm | Observed; no delivery % recorded |
| RSSI by location | Holt −103 · Vatnslíð −103 · Fish Drying Area −112 · Netto −112 · Ásvallalaug −113 dBm | Measured averages |
| Calibration | 0.0006877·ADC² − 0.5961·ADC + 127.70; 0–40 %; RMSE ≈3.01 pp | Calculated, **in-sample**, 5 levels |
| Laboratory ADC interval | ≈485 counts at 0 %; ≈197 counts at 40 % gravimetric moisture | Tested laboratory relationship, not the sensor's operating limits |
| Field baseline offsets | −254 / −341 / −332 counts (nodes 1/3/7); adjusted ADC = raw ADC + offset | Fitted after deployment using the first half of each node's paired daily observations |
| Moisture-related trend comparison | Later-period Pearson r = 0.86 / 0.76 / 0.55 (nodes 1/3/7) | Estimated permittivity vs project sensor mean; offsets held fixed |
| Later days within project sensor envelope | 53.1 / 75.0 / 88.0 % (nodes 1/3/7) | Within the range spanned by four project sensors; **not** percentage accuracy or laboratory-range coverage |
| Cloud | HTTP 200 OK; ≈1–2 s | Measured, controlled tests |
| Keldur | 4 nodes, 17 Oct 2025; depths 80/60/65/85 mm (nodes 1/3/5/7); soil layer ≈170 mm | |
| Keldur record spans | 70.8 / 129.5 / 77.5 / 50.9 days (nodes 1/3/5/7); final 3.63 / 3.49 / 3.78 / 3.93 V | First-to-last valid record, **not** battery life |
| Shared gap | ≈145 h, 17–23 Dec 2025, nodes 1, 3, 5 | Cause unknown |
| Cutoff | 3.25 V | |
| Soil-temp comparison | Pearson r 0.75–0.98; nodes colder by 0.16–3.33 °C | Trend agreement, not accuracy |
| Cost | ISK 11,921.44 per node | Appendix BOM |
| IDs | 3-bit switch → 8 IDs; 8 ledger slots; 96-byte packet | Design |

---

## A. Choices and design

### 1. Why 433 MHz?
- **Why they ask:** 868 MHz is the usual LoRa band in Europe; they want to know whether 433 MHz was a considered choice.
- **Answer:** The Ra-02 (SX1278) module operates at 433 MHz, which is within the legal ISM band in Iceland. It is long-range, low-power and small, which suits the node. The thesis notes that the choice between 433, 868 and 915 MHz depends on regional regulations and deployment requirements.
- **Remember:** 433 MHz, SX1278, 17 dBm. The thesis did **not** compare 433 MHz with 868 MHz experimentally.
- **Limitation:** 🔶 Say plainly that no frequency comparison was done; the choice was based on legality, module availability and fit for the application.

### 2. Why LoRa rather than Zigbee or NB-IoT?
- **Why they ask:** tests whether the technology was chosen deliberately.
- **Answer:** The thesis states LoRa was chosen primarily for low-power operation and reliable communication, not maximum distance. Nodes are buried and may be covered by snow, so a robust link matters even at short distances. The data are periodic and low-rate, which suits LoRa, and range gives flexibility for future sites. Literature comparison (indicative only): Zigbee about 10–300 m, LoRa 2–15 km, NB-IoT up to 100 km but dependent on cellular coverage and power.
- **Remember:** the range table in the thesis is "indicative only".
- **Limitation:** ✅

### 3. Why this network architecture (ledger mesh) rather than a star network or LoRaWAN?
- **Why they ask:** a custom protocol needs justification against standard options.
- **Answer:** The design aimed to reduce dependence on a single communication path. In a star network only the base station holds the dataset; in the ledger approach each node keeps a copy and merges what it hears, which adds data redundancy, lets nodes verify their data was incorporated, and reduces single points of failure. It was kept simple enough for an ATmega328P (text packets, additive checksum, RC4).
- **Remember:** 96-byte ledger, one slot per ID, relay only if the ledger differs from the local copy.
- **Limitation:** 🔶 There was no experimental comparison against a star topology or LoRaWAN. Multi-hop trade-offs (latency, coordination) are known from the literature and were not measured here.

### 4. Why a mesh at all, if Keldur is within single-hop range?
- **Why they ask:** challenges whether the mesh adds anything.
- **Answer:** The mesh allows nodes to forward data when direct communication is unavailable and gives flexibility for sites where nodes or the base station are farther apart. At Keldur the mesh was enabled on all four nodes, but because no base-station packet logs were kept, it is not known whether any record travelled directly or via another node.
- **Limitation:** 🔶 Do not claim the mesh was needed or used at Keldur; it is unquantified.

### 5. What exactly was demonstrated, and what was only proposed?
- **Why they ask:** the most important integrity question.
- **Answer (short table):**

| Item | Status |
|---|---|
| Four nodes built, deployed at Keldur | **Demonstrated** |
| Cloud upload (HTTP 200, ≈1–2 s) | **Demonstrated** (controlled tests) |
| Single-hop LoRa at several sites within ≈3 km | **Observed** (no delivery %) |
| Current per state; average 3.08 mA | **Measured** states, **calculated** average |
| 142-day lifetime | **Calculated estimate**, not measured |
| Calibration over 0–40 % | **Demonstrated** in the lab, in-sample |
| Reference-assisted field baseline adjustment | **Evaluated** on later observations with fixed offsets; supports moisture-related trend comparison |
| SD backup recovering missed entries | **Demonstrated** in early campus tests; **not** at Keldur |
| Mesh relay | **Observed qualitatively** on the bench; logs not retained |
| Multi-hop range, hops, latency, PDR | **Not measured** |
| Winter battery behaviour | **Not measured** |
| Absolute moisture accuracy at Keldur | **Not established** |

- **Limitation:** 🔶

### 6. Why capacitive sensors instead of TDR/FDR or resistive sensors?
- **Answer:** TDR/FDR are accurate but cost hundreds to thousands of dollars and are less suited to distributed deployment. Resistive probes are prone to corrosion and soil-dependent resistance. Capacitive sensors are low-cost, sealed and less prone to corrosion, but they need calibration, which is why the calibration work was done.
- **Limitation:** 🔶 A low-cost sensor needs per-node, ideally site-soil, calibration.

### 7. Why RC4, and is the data secure?
- **Answer:** The packet is human-readable text, so RC4 provides basic obfuscation. An initial AES implementation was considered, but it proved too computationally intensive for the ATmega328P: it introduced noticeable delays in packet preparation and hurt mesh responsiveness. RC4 is not secure for high-security use; it is a prototype compromise.
- **Remember:** RC4 state limited to 255 bytes to save RAM.
- **Limitation:** 🔶 Not a secure design; the checksum is also a simple arithmetic sum, not a CRC.

### 8. Why ThingSpeak, and what if the service changes?
- **Answer:** Selected for reliability, accessibility, low cost, ease of integration and built-in time-series visualization; the data rate fits the free tier. AWS or Azure were considered unnecessarily complex and costly for this scope. Museum staff view a shared dashboard link without account access.
- **Limitation:** 🔶 Dependence on a third-party free tier; availability during the Keldur deployment was not established.

---

## B. Communication results

### 9. How robust is the ≈3 km result?
- **Why they ask:** the headline number can be over-read.
- **Answer:** Successful single-hop communication was observed at **several test locations** within an approximate distance of 3 km, in a semi-urban area, with average RSSI between −103 and −113 dBm. Packet-delivery percentages and per-location packet counts were not recorded, so the thesis does not show that the whole 3 km area was uniformly or continuously reliable. The coverage map is an indicative estimate, not a measured boundary.
- **Remember:** −103 to −113 dBm; five locations; single-hop.
- **Limitation:** 🔶

### 10. Why were some communication results weaker?
- **Answer:** Three documented causes. (1) The first antennas were intended for Wi-Fi, not 433 MHz; replacing them with 433 MHz antennas substantially improved range and reliability. (2) Obstructions: dense residential areas, hills and structures caused degradation and occasional packet loss. (3) Antenna placement: signal improved when the node was at an elevated location. At Keldur, the cause of the December gap is unknown.
- **Limitation:** 🔶 The antenna improvement was observed, not quantified.

### 11. Did you test multi-hop?
- **Answer:** Not quantitatively. Relay was observed qualitatively on the bench (1–4 June 2025) through live debug output; the logs, topology, spacing and firmware revision were not retained. The Vellir test was single-hop only, with mesh not enabled. A controlled, logged multi-hop test is the first recommendation.
- **Limitation:** 🔶

### 12. What does RSSI of −113 dBm tell you?
- **Answer:** It is the lowest of the five average RSSI values (Ásvallalaug). The thesis does not give per-location delivery rates, so RSSI alone is not a reliability measure here.
- **Limitation:** 🔶 Do not quote a link margin: no receiver sensitivity analysis is in the thesis.

---

## C. Soil-moisture calibration

### 13. How was soil moisture calibrated?
- **Answer:** An Icelandic soil sample was oven-dried at 105 °C for 32 h, cooled, then wetted with a spray mister in 10 % steps of dry mass up to 40 % (soil approached saturation beyond). Custom sensors and a HOBO MX2307 reference were installed side by side. Gravimetric moisture is the reference. The procedure was run twice (8 November, 2069.5 g sample; 16 December, 400 g sample). The polynomial was fitted to the mean of the two sensors in Test 1.
- **Remember:** ADC from ≈485 (dry) to ≈197 (40 %).
- **Limitation:** 🔶 One soil, not Keldur soil.

### 14. Why a second-order calibration?
- **Answer:** The thesis states that the ADC-to-moisture relationship is nonlinear, so a second-order polynomial regression was used. ADC counts drop steeply from 0 to 20 % and flatten toward 40 %.
- **Be ready for (not in the thesis):** with five points and three coefficients, the fit has two degrees of freedom, so a low in-sample RMSE is expected. This is why the thesis calls the 3.01 pp an in-sample fit error, not validation, and recommends a separate validation dataset.
- **Limitation:** 🔶

### 15. What does ≈3.01 percentage-point RMSE mean in practice?
- **Answer:** At the five calibration levels (0, 10, 20, 30, 40 %), the fitted values differ from the gravimetric targets by about 3 percentage points root-mean-square. Errors are +0.35, −2.53, +5.40, −0.15, −3.10 pp (sum of squares 45.3; √(45.3/5) = 3.01). It is a fit error on the same data used to derive the polynomial. It does not predict accuracy in Keldur soil.
- **Remember:** largest single error 5.4 pp at 20 %.
- **Limitation:** 🔶

### 16. How does HOBO relate to your calibration?
- **Answer:** HOBO is a reference **trend** only. It reports volumetric water content (VWC); the polynomial is fitted against gravimetric moisture. Converting needs bulk density, which was not measured, so no RMSE against HOBO is reported. The permittivity values in the thesis are estimated from HOBO VWC by numerically inverting the Topp relationship; they are not measured by the logger.
- **Limitation:** 🔶

### 17. How were the unknown field-node baselines handled?
- **Answer to rehearse:** The field probes were not individually calibrated before installation, so their baseline offsets were unknown. We estimated a separate offset for each included node using the first half of its daily observations and the separate monitoring project's measurements. We then held each offset fixed and evaluated the later half. The agreement supports tracking moisture-related changes; absolute water content still needs co-located validation.
- **Name the method:** **Post-deployment, reference-assisted baseline adjustment.** The separate project provided a reference dataset for alignment, not a co-located calibration instrument.
- **How it was fitted:** Select an offset that maximises the fraction of early daily estimates within the range spanned by the four project sensors. Use that same offset in the later test period, without refitting. Each node has its own chronological split.
- **What was converted:** Adjusted ADC = raw ADC + offset. The comparison interpolates between laboratory ADC/permittivity pairs; it does **not** use the gravimetric-moisture polynomial to produce validated moisture percentages. Adjusted values outside the laboratory interval are omitted, not clipped or extrapolated.

| Node | ADC offset (counts) | Fit / test days | Test days within project sensor envelope | Later-period Pearson r |
|---|---|---|---|---|
| 1 | −254 | 32 / 32 | 53.1 % | 0.86 |
| 3 | −341 | 48 / 48 | 75.0 % | 0.76 |
| 7 | −332 | 25 / 25 | 88.0 % | 0.55 |

- **Explain the table:** The envelope is the minimum-to-maximum range of the four project sensors on each day, not an accuracy tolerance. The percentages include all test days in the denominator; unavailable estimates do not count as inside. Pearson r uses available paired estimates against the project sensor mean.
- **If asked about “out of range”:** That refers to the **unadjusted ADC values relative to the laboratory curve**, not the sensor's operating limits. Only 31.1 % / 0.8 % / 0 % / 0 % of raw readings were inside that interval for nodes 1/3/5/7. Applying the polynomial directly therefore extrapolates for many readings. The offset-adjusted comparison is a separate analysis; it does not retrospectively validate the earlier unadjusted moisture percentages.
- **If asked whether the offsets are the sensors' true offsets:** They are fitted alignment parameters, not independently measured instrument offsets. Differences in soil, moisture, depth and placement may contribute because the two systems were not co-located.
- **If asked whether matching trends proves accuracy:** Agreement in the later, held-out period supports temporal consistency beyond the fitting period. It does not establish absolute water-content accuracy. Say **“supports tracking changes”**, not **“proves the moisture values are correct.”**
- **Remember:** ≈485 counts corresponds to dry soil and ≈197 counts to 40 % gravimetric moisture in the laboratory. A single field reading does not identify its required offset without a reference and assumptions about comparable conditions.
- **Exclusion:** Node 5 ADC was constant at 768 for 873 of 1,836 h (47.5 %) and was excluded; the cause remains unknown.
- **Limitation:** 🔶 Absolute moisture validation requires characterised probes in site soil beside co-located reference instruments. See slide 16 and backup B15.

---

## D. Power and battery

### 18. How was power consumption measured?
- **Answer:** A Rohde & Schwarz HMP2030 supply (current resolution to 100 µA) powered the node at 4.2 V. Firmware cycled four operating states, each held 10 s, observed over three loops. The average current is a **calculated** hourly average from the measured state currents and the defined cycle: (0.3×3300 + 9.5×3 + 119.5×60 + 12.2×237)/3600 ≈ 3.08 mA.
- **Limitation:** 🔶 Not a direct one-hour average measurement.

### 19. How reliable is the ≈142-day estimate?
- **Why they ask:** Node 3 reported for 129.5 days, which looks like a confirmation.
- **Answer:** It is an idealized estimate (10,500 / 3.08 ≈ 3,409 h) using nominal capacity, ignoring low-temperature capacity loss and battery characteristics. The 60 s radio allocation is conservative and was not derived from the firmware. The Keldur spans are first-to-last valid record, with gaps, based on upload timestamps; final voltages were 3.49–3.93 V, above the 3.25 V cutoff, and the nodes have not been retrieved, so they are **not** confirmed battery lifetimes and depletion should not be given as the reason any node stopped.
- **Limitation:** 🔶

### 20. What happens in Icelandic winter temperatures?
- **Answer:** Low temperatures reduce usable battery capacity, so the real lifetime will be shorter than 142 days. This was not measured. Winter battery tests are the first power-related recommendation. Observed so far: node 1's battery voltage fell from about 4.1 V to 3.63 V over its 70.8-day span, and the final valid voltages of all four nodes were 3.49–3.93 V (Oct 2025–Feb 2026), but voltage is not a measure of remaining capacity.
- **Limitation:** 🔶

### 21. Why is the 60 s radio allocation so much more than 0.985 s of airtime?
- **Answer:** 0.985 s is the theoretical airtime of one 96-byte packet (SF10, BW 125 kHz). The 60 s is a conservative allocation for all radio-active time per hour: receiving, transmitting and relaying, processing, state transitions and overhead. The number of transmissions and retransmissions per hour was not derived, so it is not presented as calculated airtime.
- **Limitation:** 🔶

---

## E. Reliability, failure and scaling

### 22. What happens if a sensor node fails, or the base station fails?
- **Why they ask:** probes single points of failure.
- **Answer (design reasoning, not tested):** A failed node leaves its ledger slot empty; the base station uploads zeros as placeholders (so zeros mean missing data), and the other nodes continue. If the base station fails, there is no cloud upload and no hourly time sync; nodes still keep their own RTC and SD logging. The base station is a single point of failure for the cloud path. Remote health reporting and base-station logging are recommended. At Keldur, node 7 stopped giving valid records on 6 December and nodes 1, 3, 5 shared a ≈145 h gap; causes are unknown.
- **Limitation:** 🔶

### 23. How would the system scale?
- **Answer (design, not tested):** The 3-bit ID supports 8 nodes (IDs 0–7) with one ledger slot each. More identifier bits or software prefixes can extend this. The 96-byte text packet and ≈0.985 s airtime at SF10 mean larger networks bring more traffic and latency; packed binary payloads would improve efficiency. Each node uploads to its own ThingSpeak channel within free-tier limits.
- **Limitation:** 🔶 Scaling was not tested.

---

## F. Judgement and contribution

### 24. What are the main limitations of the current prototype?
- **Answer:** (1) No winter/cold battery data; (2) mesh behaviour unquantified (no packet logs; qualitative bench observation only); (3) ≈3 km is not a delivery-ratio result; (4) laboratory calibration is in-sample on separate soil over 0–40 %, while field baseline adjustment supports trends rather than absolute moisture accuracy; (5) unknown reasons why Keldur nodes stopped; SD cards not retrieved; (6) unvalidated enclosure and air-sensor placement; (7) text packets, weak checksum, RC4 obfuscation; (8) single site, one season.
- **Limitation:** 🔶

### 25. What would you change with another year?
- **Answer (thesis recommendations):** winter battery tests; improved enclosure and sensor protection, with controlled internal vs external air-sensor tests; remote node-health reporting; base-station logging of packet IDs, RSSI/SNR, forwarding and upload status; retrieve Keldur SD data; calibrate in site soil with a separate validation set and co-located reference; controlled multi-hop tests with retained logs; more sites and seasons; packed binary packets.
- **Limitation:** ✅ (these are future work, not claims)

### 26. What is the main original contribution?
- **Answer:** An integrated, low-cost, end-to-end monitoring platform, demonstrated on four turf roofs: custom-PCB nodes (≈ISK 11,921 per node), local SD backup, a ledger-style LoRa mesh relay in firmware, a base station with ThingSpeak upload, a characterised power budget, a capacitive-sensor calibration over 0–40 %, and a field deployment with lessons on antennas, air-sensor placement and calibration transfer. The thesis explicitly **does not** claim a new sensing principle or radio, and does not claim other monitoring solutions are unsuitable.
- **Limitation:** 🔶

### 27. The research question says "reliably". Did you show reliability?
- **Answer:** Partly. Feasibility is shown: a working end-to-end system on four roofs, delivering data to the cloud. Long-term reliability is not: nodes reported for 51–130 days with gaps and unexplained stops, mesh performance and absolute moisture accuracy are unquantified, and winter battery life is unknown. The conclusions state this, and the recommendations are aimed at closing it.
- **Limitation:** 🔶

### 28. What does r = 0.75–0.98 against the separate Keldur dataset prove?
- **Answer:** That the nodes captured the same temporal behaviour of soil temperature as an independent system (daily means, 18 Oct 2025–27 Jan 2026), even though nodes were on four roofs and the project sensors on one. It does not prove absolute accuracy: nodes read colder by 0.16–3.33 °C, depths and locations differ, and node timestamps are upload times.
- **Remember:** days compared: 64 / 95 / 70 / 50 (nodes 1/3/5/7); node 3 r ≥ 0.91.
- **Limitation:** 🔶

---

## Prep notes: things the committee could probe that the thesis leaves open

These come from my reading and recalculation. **Verify before quoting; they are not claims in the thesis.**

1. **Distinguish direct polynomial output from the adjusted comparison [my calculation].** The fitted parabola has its minimum at ADC ≈ 433 (output ≈ −1.5 %) and rises again for larger ADC. Direct evaluation at raw field values can therefore give misleading moisture percentages; it does not demonstrate real moisture extremes. Revised backup B15 instead shows the **offset-adjusted permittivity comparison**, which omits adjusted values outside the laboratory interval. Explain which analysis a number comes from: the later comparison supports temporal consistency but does not validate the original unadjusted moisture percentages.
2. **Test 2 does not repeat Test 1 closely [my calculation].** Test 2 sensor 1 reads 260.36 at 10 % and 265.29 at 20 % (nearly equal), versus ≈319 and ≈236 in Test 1. Applying the Test 1 polynomial to Test 2 gives errors up to ≈9 pp (RMSE ≈4.7 pp, sensor 1 only). The thesis uses Test 2 only to show consistent trends and reports the RMSE as in-sample on Test 1. If asked about repeatability, acknowledge it candidly.
3. **Zener vs diode.** The text says a Zener diode reduces the maximum input by about 0.5 V; the bill of materials lists D2 as a 1N4001 or 1N4004. Check the build before the defense and be ready to say which part is on the board.
4. **11–27 days vs 142 days.** Do not compare them: the thesis says the preliminary durations were observed with nodes under active development, with one cell, and are not full-discharge lifetimes. The single-cell estimate from the model is ≈47 days; the longest logged period was 26.8 days.
5. **Date on the title slide.** I used "February 2027" from the thesis title page. Replace it with the actual defense date.
6. **Timestamps.** ThingSpeak `created_at` is the upload time, not the RTC measurement time; the two-dataset comparison therefore has some timing uncertainty, reduced by daily averaging.
