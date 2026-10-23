#include "motor_driver.h"
#include "config.h"

QueueHandle_t g_motorQueue = nullptr;

void motorInit() {
    pinMode(MOTOR_IN1, OUTPUT); pinMode(MOTOR_IN2, OUTPUT);
    pinMode(MOTOR_IN3, OUTPUT); pinMode(MOTOR_IN4, OUTPUT);
    digitalWrite(MOTOR_IN1, LOW); digitalWrite(MOTOR_IN2, LOW);
    digitalWrite(MOTOR_IN3, LOW); digitalWrite(MOTOR_IN4, LOW);

    // ESP32 Arduino Core 3.x LEDC API
    ledcAttach(MOTOR_ENA, MOTOR_PWM_FREQ, MOTOR_PWM_RES);
    ledcAttach(MOTOR_ENB, MOTOR_PWM_FREQ, MOTOR_PWM_RES);

    g_motorQueue = xQueueCreate(5, sizeof(MotorCmd));
    Serial.println("[MOTOR] L298N Initialized (PWM @ 5kHz, Core 3.x API)");
}

void motorStop() {
    digitalWrite(MOTOR_IN1, HIGH); digitalWrite(MOTOR_IN2, HIGH);
    digitalWrite(MOTOR_IN3, HIGH); digitalWrite(MOTOR_IN4, HIGH);
    ledcWrite(MOTOR_ENA, 0);
    ledcWrite(MOTOR_ENB, 0);
}

void motorApply(const MotorCmd &cmd) {
    bool leftFwd = true, rightFwd = true;
    switch (cmd.dir) {
        case MotorDir::FORWARD:   leftFwd = true;  rightFwd = true;  break;
        case MotorDir::BACKWARD:  leftFwd = false; rightFwd = false; break;
        case MotorDir::LEFT:      leftFwd = false; rightFwd = true;  break;
        case MotorDir::RIGHT:     leftFwd = true;  rightFwd = false; break;
        default: motorStop(); return;
    }
    digitalWrite(MOTOR_IN1, leftFwd ? HIGH : LOW);
    digitalWrite(MOTOR_IN2, leftFwd ? LOW  : HIGH);
    digitalWrite(MOTOR_IN3, rightFwd ? HIGH : LOW);
    digitalWrite(MOTOR_IN4, rightFwd ? LOW  : HIGH);
    ledcWrite(MOTOR_ENA, cmd.speedL);
    ledcWrite(MOTOR_ENB, cmd.speedR);
}

void TaskMotor(void *pvParameters) {
    (void)pvParameters;
    MotorCmd cmd;
    TickType_t lastCommandTick = xTaskGetTickCount();
    Serial.println("[TASK] Motor Driver pinned to Core " + String(xPortGetCoreID()));

    for (;;) {
        if (xQueueReceive(g_motorQueue, &cmd, pdMS_TO_TICKS(100))) {
            lastCommandTick = xTaskGetTickCount();
            if (millis() - cmd.timestamp > MOTOR_WATCHDOG_MS) {
                motorStop();
                continue;
            }
            motorApply(cmd);
        } else {
            // Watchdog: Auto-stop if no command received within timeout
            if (xTaskGetTickCount() - lastCommandTick > pdMS_TO_TICKS(MOTOR_WATCHDOG_MS)) {
                motorStop();
            }
        }
    }
}
