// Deneyap Kart + Deneyap Kamera: MJPEG stream server for the kaldirim counter.
//
// Board package: install "Deneyap" boards in Arduino IDE
//   (Boards Manager URL: https://raw.githubusercontent.com/deneyapkart/deneyapkart-arduino-core/master/package_deneyapkart_index.json)
// Then select your Deneyap Kart revision. The CAM* pin macros below come from the
// board variant, so the sketch works on every revision that has the camera connector.
//
// Endpoints:
//   http://<ip>/        -> status text
//   http://<ip>/jpg     -> one JPEG frame
//   http://<ip>/stream  -> multipart MJPEG stream (what the host reads)
//
// Keep the board indoors, behind the window, well back in the room.

#include <WiFi.h>
#include "esp_camera.h"
#include "esp_http_server.h"

#ifndef CAMD2
#error "Select a Deneyap Kart board from the Deneyap board package; CAM* pin macros are missing."
#endif

// ---- fill these in ----
const char *WIFI_SSID = "YOUR_SSID";
const char *WIFI_PASS = "YOUR_PASSWORD";
// Frame size. From a high window (30 m+), use UXGA so distant riders keep enough pixels;
// the host crops the pavement strip and detects on that. Expect roughly 3-6 fps over Wi-Fi.
// Use FRAMESIZE_SVGA for a closer, lower window where frame rate matters more.
#define STREAM_FRAMESIZE FRAMESIZE_UXGA
// ------------------------

static httpd_handle_t server = nullptr;

static bool init_camera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer = LEDC_TIMER_0;
  c.pin_d0 = CAMD2;
  c.pin_d1 = CAMD3;
  c.pin_d2 = CAMD4;
  c.pin_d3 = CAMD5;
  c.pin_d4 = CAMD6;
  c.pin_d5 = CAMD7;
  c.pin_d6 = CAMD8;
  c.pin_d7 = CAMD9;
  c.pin_xclk = CAMXC;
  c.pin_pclk = CAMPC;
  c.pin_vsync = CAMV;
  c.pin_href = CAMH;
  c.pin_sccb_sda = CAMSD;
  c.pin_sccb_scl = CAMSC;
  c.pin_pwdn = -1;
  c.pin_reset = -1;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size = STREAM_FRAMESIZE;
  c.jpeg_quality = 12;             // lower = better quality, bigger frames
  c.fb_count = psramFound() ? 2 : 1;
  c.grab_mode = CAMERA_GRAB_LATEST;
  c.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;

  if (esp_camera_init(&c) != ESP_OK) return false;

  sensor_t *s = esp_camera_sensor_get();
  if (s) {
    s->set_vflip(s, 0);      // flip if the module is mounted upside down
    s->set_hmirror(s, 0);
    s->set_brightness(s, 0);
    s->set_saturation(s, 0);
  }
  return true;
}

static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/plain");
  String s = "kaldirim cam ok\nip=" + WiFi.localIP().toString() + "\nrssi=" + String(WiFi.RSSI()) + "\n";
  return httpd_resp_send(req, s.c_str(), s.length());
}

static esp_err_t jpg_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  esp_err_t r = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return r;
}

static const char *BOUNDARY = "frame";

static esp_err_t stream_handler(httpd_req_t *req) {
  char hdr[96];
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) return ESP_FAIL;
    int n = snprintf(hdr, sizeof(hdr),
                     "\r\n--%s\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                     BOUNDARY, (unsigned)fb->len);
    esp_err_t r = httpd_resp_send_chunk(req, hdr, n);
    if (r == ESP_OK) r = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (r != ESP_OK) return r;   // client went away
  }
}

static void start_server() {
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.server_port = 80;
  if (httpd_start(&server, &cfg) != ESP_OK) return;
  httpd_uri_t u_index = { "/", HTTP_GET, index_handler, nullptr };
  httpd_uri_t u_jpg = { "/jpg", HTTP_GET, jpg_handler, nullptr };
  httpd_uri_t u_stream = { "/stream", HTTP_GET, stream_handler, nullptr };
  httpd_register_uri_handler(server, &u_index);
  httpd_register_uri_handler(server, &u_jpg);
  httpd_register_uri_handler(server, &u_stream);
}

static void connect_wifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);            // keeps the stream smooth
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("wifi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println();
  Serial.print("ip: "); Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(200);
  if (!init_camera()) {
    Serial.println("camera init failed; check the flex cable seating");
    while (true) delay(1000);
  }
  connect_wifi();
  start_server();
  Serial.println("stream: http://" + WiFi.localIP().toString() + "/stream");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("wifi lost, reconnecting");
    WiFi.disconnect();
    connect_wifi();
  }
  delay(2000);
}
