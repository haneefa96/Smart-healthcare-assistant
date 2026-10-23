# Smart Healthcare Assistant Robot Using ESP32-S3

[![ESP32-S3](https://img.shields.io/badge/Platform-ESP32--S3-red.svg)](https://www.espressif.com/en/products/socs/esp32-s3)
[![Framework](https://img.shields.io/badge/Framework-Arduino%20%2F%20ESP--IDF-blue.svg)](https://docs.espressif.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Prototype%20Architecture-orange.svg)](#)

An intelligent, embedded-system-based robotic prototype engineered to deliver routine patient care assistance. The system combines **AI-powered voice interaction**, **non-invasive vitals monitoring (Heart Rate & SpO₂)**, **teleoperated differential drive mobility**, and an **integrated web management portal**, all orchestrated by the dual-core **ESP32-S3** microcontroller.

---

## Table of Contents
1. [Project Synopsis](#project-synopsis)
2. [Key Objectives](#key-objectives)
3. [System Architecture Overview](#system-architecture-overview)
4. [Hardware Bill of Materials (BOM)](#hardware-bill-of-materials-bom)
5. [Pinout & Complete Wiring Specification](#pinout--complete-wiring-specification)
   - [Power Distribution Network (PDN)](#power-distribution-network-pdn)
   - [INMP441 I2S Microphone](#inmp441-i2s-microphone)
   - [MAX98357A I2S Audio Amplifier](#max98357a-i2s-audio-amplifier)
   - [MAX30102 Pulse Oximeter & OLED I2C Bus](#max30102-pulse-oximeter--oled-i2c-bus)
   - [L298N Dual H-Bridge Motor Driver](#l298n-dual-h-bridge-motor-driver)
6. [Software & Subsystem Architecture](#software--subsystem-architecture)
7. [Development & Implementation Roadmap](#development--implementation-roadmap)
8. [Safety & Medical Disclaimer](#safety--medical-disclaimer)

---

## Project Synopsis

The **Smart Healthcare Assistant Robot** is an interactive, mobile embedded assistant designed to reduce hospital staff fatigue and assist elderly or recovering patients in healthcare or home-care settings. 

Powered by the high-performance **ESP32-S3** (Xtensa® 32-bit LX7 dual-core, AI vector instructions, Wi-Fi 4 + BLE 5.0), the robot coordinates real-time audio acquisition, speech-based AI reasoning, photoplethysmography (PPG) vitals acquisition, and motor actuation.

```
       +---------------------------------------------------------------+
       |                   PATIENT / HEALTHCARE USER                   |
       +---------------------------------------------------------------+
                 ^ Voice Audio In               | Audio Out / Visual
                 |                              v
       +--------------------+       +----------------------------------+
       | INMP441 Microphone |       | MAX98357A Amp + OLED SSD1306     |
       +--------------------+       +----------------------------------+
                 | (I2S DMA)                    ^ (I2S DMA / I2C)
                 v                              |
       +---------------------------------------------------------------+
       |             ESP32-S3 Microcontroller (Dual Core)              |
       |  Core 0: Network Server, Audio Streaming, AI Backend Gateway  |
       |  Core 1: Sensor Sampling, Motor PWM, Failsafe Watchdogs       |
       +---------------------------------------------------------------+
           |                     |                           |
 (Wi-Fi WebSocket/HTTP)      (I2C Bus)                  (LEDC PWM)
           v                     v                           v
+---------------------+ +-----------------+       +--------------------+
| Local/Cloud AI Hub  | | MAX30102 Sensor |       | L298N Motor Driver |
| STT -> LLM -> TTS   | | (HR & SpO2 PPG) |       | + Dual DC Motors   |
+---------------------+ +-----------------+       +--------------------+
```

---

## Key Objectives

- **Conversational Voice Assistant**: Provide natural hands-free verbal interaction using an INMP441 digital microphone, an offloaded AI pipeline (STT $\to$ LLM $\to$ TTS), and a MAX98357A Class-D amplifier.
- **Continuous Vitals Telemetry**: Non-invasively compute instantaneous Heart Rate (BPM) and peripheral capillary oxygen saturation ($\text{SpO}_2$) with the MAX30102 optical sensor.
- **Local Glanceable Display**: Present vitals, connection statuses, battery level, and visual expressions on a 0.96"/1.3" I2C OLED display.
- **Teleoperated Mobility**: Provide responsive differential drive navigation via an intuitive, mobile-friendly web controller served directly by the ESP32-S3.
- **Fail-Safe Operation**: Implement dead-man switch timeouts, motor braking on signal loss, and regulated battery telemetry.
- **Low-Cost Modular Architecture**: Establish an educational, easily reproducible, open-hardware reference platform.

---

## System Architecture Overview

| Subsystem | Hardware Controller | Communication Protocol | Operational Responsibility |
|---|---|---|---|
| **Audio Capture** | INMP441 MEMS Mic | I2S0 (DMA RX) | 16 kHz, 16-bit Mono digital PCM streaming |
| **Audio Playback** | MAX98357A Class-D Amp | I2S1 (DMA TX) / I2S Shared | High-efficiency speech audio synthesis output |
| **Health Sensing** | MAX30102 PPG Sensor | I2C (Bus 0: 400 kHz Fast-Mode) | Raw Red & IR LED reflectance sampling |
| **Onboard Display** | SSD1306 128x64 OLED | I2C (Bus 0: Shared at 0x3C) | Real-time waveform, BPM, $\text{SpO}_2$, robot avatar |
| **Mobility & Drive** | L298N Dual H-Bridge | GPIO + LEDC PWM (Core 1) | Differential steering: Forward, Reverse, Spin, Stop |
| **Web Server & UI** | ESP32-S3 WiFi (AP/STA) | HTTP REST / WebSockets | Touch joystick controls & live telemetry streaming |
| **AI Cloud Gateway** | Backend Service | TCP / REST / WebSockets | Whisper/Vosk (STT), Gemini/LLM, Edge-TTS/Piper |

---

## Hardware Bill of Materials (BOM)

| Item | Component | Specification / Rating | Quantity | Role / Purpose |
|---|---|---|---|---|
| **1** | ESP32-S3 DevKit | ESP32-S3-WROOM-1 (N16R8 / N8R2) | 1 | Central controller with dual-core processing & Wi-Fi |
| **2** | INMP441 Microphone | Omnidirectional MEMS, I2S Digital | 1 | Clear digital voice capture without analog noise |
| **3** | MAX98357A Audio DAC | Class-D Amplifier, 3.2W into 4Ω | 1 | Digital I2S to high-efficiency audio amplifier |
| **4** | Speaker | 4Ω 3W or 8Ω 2W enclosed cavity | 1 | Audio feedback and robot conversational speech |
| **5** | MAX30102 Sensor | Pulse Oximeter & Heart-Rate Sensor | 1 | Optical reflection sensor (Red 660nm + IR 880nm) |
| **6** | OLED Display | SSD1306 0.96" 128x64 I2C | 1 | Real-time display for vitals and status UI |
| **7** | L298N Motor Driver | Dual H-Bridge, up to 2A per channel | 1 | High-current DC motor speed and direction driver |
| **8** | DC Geared Motors | TT Geared Motors (1:48 ratio, 3-6V) | 2 | Differential propulsion drive wheels |
| **9** | Robot Chassis Kit | 2-Wheel + 1 Caster acrylic/metal chassis | 1 | Structural robotic platform |
| **10** | Battery Pack | 2x 18650 Li-ion cells in series (2S 7.4V) | 1 | Main primary power supply |
| **11** | 2S BMS Module | 2S 7.4V 8.4V Li-ion Battery Protection | 1 | Over-charge, over-discharge & short circuit safety |
| **12** | DC-DC Step Down | LM2596 or MP1584 Buck Converter | 1 | Regulates 7.4V battery pack down to stable 5.0V |
| **13** | Switch & Fuse | SPST Rocker Switch + 2.5A Fast Blow Fuse | 1 | Master power isolation & overcurrent protection |
| **14** | Logic Level / Wires | Silicone jumper wires, breadboard/perfboard | Lot | Point-to-point interconnects & bus lines |

---

## Pinout & Complete Wiring Specification

### Power Distribution Network (PDN)

```
[2x 18650 Battery Pack: 7.4V Nominal / 8.4V Peak]
        |
      [2S BMS Protection Board]
        |
    [2.5A Inline Fuse]
        |
   [Master ON/OFF Switch]
        |
        +-----------------------------------> [L298N VMS (Motor 7.4V Power)]
        |
    [DC-DC Buck Converter (Step down to 5.00V)]
        |
        +---> [ESP32-S3 5V/VIN Pin]
        +---> [MAX98357A VIN Pin (for maximum output volume)]
        |
[ESP32-S3 Onboard 3.3V LDO Output]
        |
        +---> [INMP441 VDD (3.3V)]
        +---> [MAX30102 VIN (3.3V)]
        +---> [SSD1306 OLED VCC (3.3V)]
        |
[COMMON SYSTEM GROUND]
        +=== Interconnect: Battery GND, BMS GND, Buck GND, ESP32 GND, L298N GND, Sensors GND
```

> [!CAUTION]
> **Ground Loop & Level Isolation**: Always interconnect all ground terminals into a single low-impedance star ground. **Never** power the ESP32 3.3V rail directly from an unregulated power source. Calibrate the Buck converter output with a multimeter to precisely **5.00V** before making connections to the ESP32 5V/VIN pin.

---

### INMP441 I2S Microphone

| INMP441 Pin | ESP32-S3 Pin | Function | Notes |
|---|---|---|---|
| **VDD** | `3V3` | Power Supply | 3.3V Clean logic rail |
| **GND** | `GND` | Ground | System common ground |
| **SCK** | `GPIO 4` | Continuous Serial Clock (BCLK) | Clock output from ESP32 master |
| **WS** | `GPIO 5` | Word Select (LRCLK) | Framing clock (Left / Right channel) |
| **SD** | `GPIO 6` | Serial Data Out (DIN) | Serial microphone data to ESP32 |
| **L/R** | `GND` | Channel Select | Tied to GND selects Left Audio Channel |

---

### MAX98357A I2S Audio Amplifier

| MAX98357A Pin | ESP32-S3 / Power | Function | Notes |
|---|---|---|---|
| **VIN** | `5V (Buck Output)` | Power Supply | 5V provides 3.2W output into 4Ω |
| **GND** | `GND` | Ground | Common ground |
| **BCLK** | `GPIO 4` | Bit Clock | Synchronized with audio bit stream |
| **LRC** | `GPIO 5` | Word Select / Frame Sync | Audio sample framing clock |
| **DIN** | `GPIO 7` | Serial Audio Data In | ESP32 I2S DOUT transmission pin |
| **GAIN** | `GND` or `100kΩ` | Gain Setting | Defaults to 9dB (float) or 12dB (to GND) |
| **SD_MODE** | Floating / Pullup | Shutdown & Channel | Unconnected mixes (L+R)/2 |
| **SPK+** | Speaker (+) Terminal | Balanced Positive Output | Direct connection; **NEVER** connect to GND |
| **SPK-** | Speaker (-) Terminal | Balanced Negative Output | Direct connection; **NEVER** connect to GND |

---

### MAX30102 Pulse Oximeter & OLED I2C Bus

*Both modules share the primary hardware I2C peripheral on the ESP32-S3.*

| Peripheral Pin | ESP32-S3 Pin | I2C Address | Notes |
|---|---|---|---|
| **MAX30102 VCC** | `3V3` | - | Operating voltage: 1.8V - 3.3V |
| **MAX30102 GND** | `GND` | - | Common ground |
| **MAX30102 SDA** | `GPIO 8` | `0x57` | I2C Data (4.7kΩ pull-up to 3.3V) |
| **MAX30102 SCL** | `GPIO 9` | `0x57` | I2C Clock (4.7kΩ pull-up to 3.3V) |
| **MAX30102 INT** | `Unconnected` / `GPIO 21` | - | Optional hardware data-ready interrupt |
| **OLED VCC** | `3V3` | - | 3.3V logic rail |
| **OLED GND** | `GND` | - | Common ground |
| **OLED SDA** | `GPIO 8` | `0x3C` (or `0x3D`) | Shared I2C Data bus |
| **OLED SCL** | `GPIO 9` | `0x3C` (or `0x3D`) | Shared I2C Clock bus |

---

### L298N Dual H-Bridge Motor Driver

| L298N Pin | ESP32-S3 Pin | Hardware Type | Function / Description |
|---|---|---|---|
| **IN1** | `GPIO 10` | Standard GPIO | Left Motor Direction Bit 1 |
| **IN2** | `GPIO 11` | Standard GPIO | Left Motor Direction Bit 2 |
| **IN3** | `GPIO 12` | Standard GPIO | Right Motor Direction Bit 1 |
| **IN4** | `GPIO 13` | Standard GPIO | Right Motor Direction Bit 2 |
| **ENA** | `GPIO 14` | LEDC PWM (CH 0) | Left Motor Speed Control (Remove jumper) |
| **ENB** | `GPIO 15` | LEDC PWM (CH 1) | Right Motor Speed Control (Remove jumper) |
| **OUT1, OUT2** | Motor Left (+/-) | High Current Out | Left DC Geared Drive Motor |
| **OUT3, OUT4** | Motor Right (+/-) | High Current Out | Right DC Geared Drive Motor |
| **12V (VMS)** | `+7.4V Pack` | Switched DC In | High-power motor rail from battery |
| **GND** | `System GND` | Power Ground | Must connect to ESP32 common ground |
| **5V Logic** | `Open / Output` | Internal Regulator | Keep 5V regulator jumper enabled if battery < 12V |

---

## Software & Subsystem Architecture

The software architecture is modularized into four distinct layers:

```
+-------------------------------------------------------------------------+
|                  APPLICATION & INTERFACE LAYER                          |
|  - Web UI Joystick Controller (HTML5 / Vanilla CSS / WebSocket)         |
|  - OLED UI Rendering (SSD1306 ASCII/Graphics Driver)                   |
+-------------------------------------------------------------------------+
                                    |
+-------------------------------------------------------------------------+
|                    ESP32-S3 FIRMWARE OS LAYER                           |
|  - FreeRTOS Task Scheduler                                              |
|    * Task_Audio (Priority 5, Core 0): I2S Ring Buffer & Streaming       |
|    * Task_Sensors (Priority 3, Core 1): MAX30102 PPG FIFO Sample & Calc |
|    * Task_Drive (Priority 4, Core 1): Direction logic & PWM duty ramps  |
|    * Task_Web (Priority 2, Core 0): Asynchronous Web Server & REST      |
+-------------------------------------------------------------------------+
                                    |
+-------------------------------------------------------------------------+
|                    BACKEND AI COGNITIVE PIPELINE                        |
|  - Ingest: Fast WebSocket / Chunked HTTP Audio Receiver                 |
|  - Speech-To-Text (STT): OpenAI Whisper / Vosk Local Engine             |
|  - Reasoning & Safety (LLM): Google Gemini / GPT-4o / Ollama           |
|  - Text-To-Speech (TTS): Piper Neural Voice / Edge-TTS                 |
|  - Transcode: 16-bit PCM 16kHz audio stream returned to ESP32          |
+-------------------------------------------------------------------------+
```

1. **Module 1: Health Monitoring**: Acquires infrared and red PPG data from MAX30102 FIFO. Applies DC removal filters, calculates peak intervals for Heart Rate (BPM), and computes Ratio-of-Ratios for $\text{SpO}_2$.
2. **Module 2: Teleoperation UI**: Hosts an embedded, mobile-responsive web dashboard with virtual directional keys, speed sliders, and live vitals telemetry.
3. **Module 3: AI Voice Assistant Pipeline**: Manages continuous audio capture via I2S, executes local silence detection, streams audio chunks to an AI backend server, and reproduces synthetic audio streams through the I2S speaker.
4. **Module 4: Safety & Motor Controller**: Encapsulates motor driving with hardware PWM ramping, dead-man watchdog safety (auto-stop after 500ms without heartbeats), and battery voltage monitoring.

---

## Development & Implementation Roadmap

1. **Step 1: Board Setup & Environment Validation**
   - Install ESP32 Board Package (v3.x+) in Arduino IDE / PlatformIO.
   - Test GPIO toggling, serial logging at 115200 baud, and verify PSRAM availability.
2. **Step 2: Vitals & I2C Verification**
   - Run I2C Scanner to verify addresses (`0x3C` for OLED, `0x57` for MAX30102).
   - Test Heart Rate and $\text{SpO}_2$ measurement stability under ambient lighting conditions.
3. **Step 3: OLED UI Integration**
   - Construct responsive UI displaying real-time pulse waveforms, battery percentage, and status indicators.
4. **Step 4: Motor & Teleoperation Rigging**
   - Benchmark L298N PWM response at 5 kHz frequency.
   - Build and serve the mobile-friendly web controller over local Wi-Fi SoftAP/Station mode.
5. **Step 5: I2S Audio Bring-Up**
   - Verify INMP441 microphone recording using WAV generation or streaming test.
   - Verify MAX98357A playback using sine-wave generation and sample WAV audio files.
6. **Step 6: AI Backend Implementation**
   - Deploy Python FastAPI or Node.js AI backend hosting STT, LLM, and TTS pipelines.
7. **Step 7: Full System Integration & Field Testing**
   - Mount electronics on chassis, balance weight distribution, benchmark battery endurance, and calibrate failsafe logic.

---

## Safety & Medical Disclaimer

> [!WARNING]
> **Educational Prototype Only**: This device is developed strictly for engineering research, educational demonstrations, and prototyping purposes. The vitals estimates generated by the MAX30102 are not medically certified, diagnostic, or therapeutic. This device must never be used in life-critical patient monitoring scenarios or to replace professional medical assessment.

---

## Documentation Index
- Detailed Engineering System Design: [DESIGN.md](file:///home/jeevan/nexathon/DESIGN.md)
- Complete System Architecture & Flow Diagrams: [architer.md](file:///home/jeevan/nexathon/architer.md)
