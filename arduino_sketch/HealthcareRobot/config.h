#pragma once

// ╔══════════════════════════════════════════════════════════════════════════╗
// ║   config.h — Hardware Pinouts, Network Settings & DSP Constants         ║
// ╚══════════════════════════════════════════════════════════════════════════╝

// ── Wi-Fi Credentials ────────────────────────────────────────────────────────
#define WIFI_SSID           "Jeevan"      // ← Replace with your Wi-Fi SSID
#define WIFI_PASSWORD       "PASSWORD"         // ← Replace with your Wi-Fi Password

// ── AI Voice Gateway Backend (Running backend/server.py on laptop) ────────────
#define AI_GATEWAY_WS       "ws://10.245.210.1:8765/ws/audio"
#define DASHBOARD_URL       "http://10.245.210.1:8765"

// ── I2S Audio Bus (Shared SCK & WS for Mic & Speaker) ────────────────────────
#define I2S_PORT            I2S_NUM_0
#define I2S_SCK_PIN         4    // BCLK / SCLK (Shared INMP441 & MAX98357A)
#define I2S_WS_PIN          5    // LRC / WS   (Shared INMP441 & MAX98357A)
#define I2S_MIC_SD_PIN      6    // SD Data In (INMP441 -> ESP32 RX)
#define I2S_SPK_DIN_PIN     7    // DIN Data Out (ESP32 TX -> MAX98357A)
#define I2S_SAMPLE_RATE     16000
#define I2S_BITS            16
#define I2S_DMA_FRAME       512
#define I2S_DMA_BUFS        8

// ── I2C Bus (Shared by MAX30102 PPG & SSD1306 OLED) ──────────────────────────
#define I2C_SDA_PIN         8
#define I2C_SCL_PIN         9
#define OLED_I2C_ADDR       0x3C
#define MAX30102_I2C_ADDR   0x57
#define OLED_WIDTH          128
#define OLED_HEIGHT         64

// ── L298N Dual H-Bridge Motor Driver ─────────────────────────────────────────
#define MOTOR_IN1           10   // Left Motor Direction 1
#define MOTOR_IN2           11   // Left Motor Direction 2
#define MOTOR_IN3           12   // Right Motor Direction 1
#define MOTOR_IN4           13   // Right Motor Direction 2
#define MOTOR_ENA           14   // Left Motor PWM (Speed)
#define MOTOR_ENB           15   // Right Motor PWM (Speed)
#define MOTOR_PWM_FREQ      5000
#define MOTOR_PWM_RES       8    // 8-bit resolution (0 to 255)
#define MOTOR_WATCHDOG_MS   500  // Fail-safe: Auto-stop if no command received for 500ms

// ── MAX30102 Optical PPG Settings ────────────────────────────────────────────
#define PPG_SAMPLE_RATE     100
#define PPG_LED_POWER       0x2F
#define PPG_SAMPLE_AVG      4
#define PPG_PULSE_WIDTH     411
#define PPG_ADC_RANGE       16384
#define HR_BUF_SIZE         10
#define FINGER_THRESHOLD    50000UL
