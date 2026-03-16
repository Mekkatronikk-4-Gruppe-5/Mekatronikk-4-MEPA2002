namespace {

constexpr long kBaudrate = 115200;
constexpr size_t kMaxCommandLength = 63;
constexpr int kLedPin = LED_BUILTIN;

char command_buffer[kMaxCommandLength + 1];
size_t command_length = 0;

void handle_command(const char *command) {
  if (strcmp(command, "PING") == 0) {
    Serial.println("PONG");
    return;
  }

  if (strcmp(command, "ID") == 0) {
    Serial.println("MEGA_SMOKETEST");
    return;
  }

  if (strcmp(command, "LED ON") == 0) {
    digitalWrite(kLedPin, HIGH);
    Serial.println("OK LED ON");
    return;
  }

  if (strcmp(command, "LED OFF") == 0) {
    digitalWrite(kLedPin, LOW);
    Serial.println("OK LED OFF");
    return;
  }

  if (strcmp(command, "LED TOGGLE") == 0) {
    digitalWrite(kLedPin, !digitalRead(kLedPin));
    Serial.println("OK LED TOGGLE");
    return;
  }

  Serial.println("ERR UNKNOWN");
}

void reset_command_buffer() {
  command_length = 0;
  command_buffer[0] = '\0';
}

}  // namespace

void setup() {
  pinMode(kLedPin, OUTPUT);
  digitalWrite(kLedPin, LOW);

  Serial.begin(kBaudrate);
  while (!Serial && millis() < 3000) {
  }

  reset_command_buffer();
  Serial.println("MEGA_READY");
}

void loop() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());

    if (c == '\r') {
      continue;
    }

    if (c == '\n') {
      command_buffer[command_length] = '\0';
      if (command_length > 0) {
        handle_command(command_buffer);
      }
      reset_command_buffer();
      continue;
    }

    if (command_length < kMaxCommandLength) {
      command_buffer[command_length++] = c;
    }
  }
}
