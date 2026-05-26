#include <Arduino.h>
#include <esp_log.h>
#include <esp_system.h>
#include <soc/rtc_cntl_reg.h>

#include "app/App.h"
#include "board/BoardConfig.h"

App app;

void rebootToDownloadMode() {
  ESP_LOGI("main", "Rebooting to download mode...");
  delay(500);  // Wait for USB to stabilize
  REG_WRITE(RTC_CNTL_OPTION1_REG, RTC_CNTL_FORCE_DOWNLOAD_BOOT);
  esp_restart();
  while(1);  // Should never reach here
}

void setup() {
  Serial.begin(115200);
  esp_log_level_set("*", ESP_LOG_INFO);
  delay(50);
  BoardConfig::begin();
  const uint32_t serialWaitStart = millis();
  while (!Serial && millis() - serialWaitStart < 2000) {
    delay(10);
  }
  Serial.println("[main] app setup");
  app.begin();
}

void loop() {
  // Check for serial command to enter download mode
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    Serial.printf("[main] cmd: '%s'\n", cmd.c_str());
    if (cmd == "download") {
      rebootToDownloadMode();
    }
  }

  const uint32_t now = millis();
  app.update(now);
}
