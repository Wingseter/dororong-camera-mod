# GENERAL-UVC / DC23 — macOS 분석 보고서

> 분석 일시: 2026-03-21
> 환경: macOS Darwin 25.3.0, Apple Silicon (ARM64)
> Python 3.14.3, PyUSB 1.3.1, ffmpeg 8.1

> **표기 규칙**: [확인] 직접 측정/검증 완료 · [추정] 근거 있으나 확정 불가 · [미확인] 추가 검증 필요

## 1. 장치 인식 상태 [확인]

| 항목 | 값 |
|------|-----|
| USB Product Name | `GENERAL - UVC` |
| USB Vendor Name | `GENERAL` |
| Vendor ID | `0x1B3F` (6975) |
| Product ID | `0x2002` (8194) |
| bcdDevice | `0x0100` (1.00) |
| bcdUSB | `0x0200` (USB 2.0) |
| USB Speed | High Speed (480 Mbps) |
| Power | 200mA (self-powered, 0xC0) |
| bDeviceClass | `0xEF` (Miscellaneous — IAD) |
| Serial Number | 없음 (iSerialNumber=0) |
| Configurations | 1 |
| Interfaces | 4 |

## 2. 펌웨어 버전 문자열 [확인] + 해석 [추정]

**USB String Descriptor #3: `Demo 1.00`** [확인]

| String Index | 값 |
|-------------|-----|
| #1 | `GENERAL` (Manufacturer) |
| #2 | `GENERAL - UVC ` (Product) |
| #3 | `Demo 1.00` ← **펌웨어 버전 문자열** |
| #4 | `GENERAL - AUDIO` |
| #5 | ` ` (공백) |

해석 [추정]:
- "Demo"라는 키워드는 Generalplus SDK의 평가/데모 펌웨어를 시사하지만, 이것만으로 SDK 기본 펌웨어임을 증명하지는 못함
- OEM이 "Demo"를 제품명으로 의도적으로 사용했을 가능성도 배제할 수 없음
- 확정하려면 동일 SoC의 다른 제품 펌웨어 버전 문자열과 비교 필요

## 3. USB 인터페이스 구조 [확인]

```
GENERAL - UVC@02100000 (IOUSBHostDevice)
├── Interface 0: Video Control (UVC)
│   ├── bInterfaceClass: 0x0E (Video)
│   ├── bInterfaceSubClass: 0x01 (Video Control)
│   ├── Endpoint 0x81 IN (Interrupt, 64B, 10ms)
│   └── Owner: UVCAssistant (pid 642)
│
├── Interface 1: Video Streaming (UVC)
│   ├── bInterfaceClass: 0x0E (Video)
│   ├── bInterfaceSubClass: 0x02 (Video Streaming)
│   ├── Alt 0: Zero bandwidth (0 endpoints)
│   ├── Alt 1: Endpoint 0x87 IN (Isochronous, 1024B, interval=1)
│   └── Owner: UVCAssistant (pid 642)
│
├── Interface 2: Audio Control
│   ├── bInterfaceClass: 0x01 (Audio)
│   ├── bInterfaceSubClass: 0x01 (Audio Control)
│   └── Owner: usbaudiod (pid 31201)
│
└── Interface 3: Audio Streaming
    ├── bInterfaceClass: 0x01 (Audio)
    ├── bInterfaceSubClass: 0x02 (Audio Streaming)
    ├── Alt 0: Zero bandwidth (0 endpoints)
    ├── Alt 1: Endpoint 0x86 IN (Isochronous, 192B, interval=4)
    └── Owner: usbaudiod (pid 31201)
```

## 4. UVC 비디오 제어 분석 [확인]

### 4.1 UVC 시그널 체인

```
Camera Input Terminal (ID=1)
    │  Type: ITT_CAMERA (0x0201)
    │  Controls: 0x0000 (없음!)
    │  Focal Length: 0 (미지정)
    ▼
Selector Unit (ID=4)
    │  Inputs: 1 (pass-through)
    ▼
Processing Unit (ID=5)
    │  Controls: 0x0001 (Brightness만)
    │  Max Multiplier: 0x0000
    ▼
Output Terminal (ID=3)
    Type: TT_STREAMING (0x0101)
```

### 4.2 UVC 컨트롤 지원 현황 [확인]

**Camera Terminal Controls (ID=1): bmControls = 0x0000** — 모든 카메라 컨트롤 비활성

**Processing Unit Controls (ID=5): bmControls = 0x0001** — Brightness만 지원

**Extension Unit: 없음** — 벤더 확장 UVC 유닛 미존재

### 4.3 UVC 클록 [확인]

dwClockFrequency: 6,000,000 Hz (6 MHz)

## 5. 비디오 스트리밍 분석 [확인]

### 5.1 포맷/프레임 디스크립터

단일 포맷(MJPEG), 단일 프레임(1280×720), 고정 30fps.

### 5.2 스틸 이미지 캡처

Still Capture Method 2 + Hardware Trigger 지원. 단, 스틸 해상도도 1280×720 제한.

### 5.3 Color Format

Color Primaries / Transfer Characteristics / Matrix Coefficients 모두 0 (Unspecified).

## 6. 오디오 분석 [확인]

USB 오디오 스트리밍: 8,000 Hz, 16-bit, mono (독립 녹화 16kHz의 절반).
Feature Unit: Mute + Volume 제어 가능 (디스크립터 확인).

캡처 테스트 결과: 완전 무음 (모든 샘플 = 0) [확인]
무음 원인 [미확인]: 기본 Mute, macOS 마이크 권한, Audio MIDI Setup 레벨, avfoundation 디바이스 인덱스 지정 등 추가 확인 필요.

## 7. ffmpeg/AVFoundation 캡처 테스트 [확인]

### 7.1 해상도 처리

| 요청 해상도 | 실제 결과 | 상태 |
|------------|----------|------|
| 기본값 (미지정) | 1920×1080 | ✅ 정상 |
| 1920×1080 | 1920×1080 | ✅ 정상 |
| 1280×720 | 1280×720 | ❌ 손상 (녹색 프레임) |

**확인된 것**: ffmpeg의 AVFoundation 입력 경로에서 720p 직접 요청 시 `Configuration of video device failed, falling back to default` 오류 발생. 1080p는 정상 캡처됨.

**Upscale 검증 [확인]**: 1080p 프레임의 Laplacian 비율 0.64 → 720p에서 업스케일된 것으로 판단.

**한계 [미확인]**: 이 결과는 ffmpeg/AVFoundation 경로 한정. AVCaptureDevice.formats 열거 또는 QuickTime/OBS 교차 확인이 되면 장치 제한인지 ffmpeg 협상 문제인지 구분 가능.

### 7.2 캡처 화질 비교

| 지표 | macOS (ffmpeg) | Windows 기본 | Windows 보정 후 |
|------|---------------|-------------|----------------|
| 밝기 | 125.4 | 55.65 | 111.3 |
| 선명도 (Lap) | 302.4 (1080p) | 9.08 | 169.8 |
| 색균형 | R=126 G=126 B=124 | 녹색 색조 | 보정 후 개선 |
| 동적 범위 | 0~255 | 6~185 | 0~255 |

macOS 경유 캡처가 Windows 기본 캡처보다 양호 [확인]. 원인은 macOS UVCAssistant의 밝기 자동 보정 [추정] 또는 OS별 기본값 차이 [추정].

## 8. Vendor-Specific USB 요청 [확인]

웹캠 모드(PID 0x2002):
- Vendor Device Requests (0xC0), bRequest 0x00~0x1F: 모두 응답 없음
- Vendor Interface Requests (0xC1): 모두 응답 없음
- High-Range Requests (0x80~0xFF): 모두 응답 없음

저장장치 모드(PID 0x0C52):
- Vendor Device Requests (0xC0), bRequest 0x00~0x2F: 모두 응답 없음
- Vendor Interface Requests (0xC1): 모두 응답 없음
- High-Range Requests (0x80~0xFF): 모두 응답 없음
- SCSI Vendor Commands (0xC0~0xFF): macOS 커널 드라이버 점유로 직접 접근 불가

**참고**: SCSI 벤더 명령은 macOS에서만 소진. Linux나 Windows/libusb 환경에서 추가 시도 가치 있음.

## 9. 저장장치 모드 분석 [확인]

### 9.1 USB 디스크립터

VID:PID = 0x1B3F:0x0C52. Interface: Mass Storage (0x08), SCSI (0x06), BOT (0x50). SCSI Vendor: `GENPLUS`, Product: `USB-MSDC DISK A`, Revision: `1.00`.

저장장치 모드에서는 String #3 ("Demo 1.00")이 노출되지 않음 — 웹캠 모드에서만 확인 가능.

### 9.2 FAT32 구조 분석

```
전체 디스크: 7,744,512 sectors (3.96 GB)

[MBR: 절대 섹터 0] — 비표준 (RRaA/rrAa FSInfo 시그니처 포함)
[MBR 갭: 절대 섹터 1-2047] — 완전 비어있음 (1 MB)
[VBR: 절대 섹터 2048 (파티션 상대 섹터 0)] — OEM: MSDOS5.0
[FSInfo: 절대 섹터 2049 (파티션 상대 섹터 1)]
[Backup Boot: 절대 섹터 2054 (파티션 상대 섹터 6)]
[Reserved: 파티션 상대 섹터 0-1291] — 1292 sectors (646 KB, 비정상적으로 큼)
[FAT1: 파티션 상대 섹터 1292-8837]
[FAT2: 파티션 상대 섹터 8838-16383]
[Data: 파티션 상대 섹터 16384+] — 965,760 clusters × 4096 bytes
```

**볼륨 레이블 참고**: `SD`는 OS가 마운트 시 보여주는 FAT 디렉터리 레이블, `NO NAME`은 VBR BPB에 기록된 볼륨 레이블. 둘 다 동시에 참이며 출처가 다름.

### 9.3 예약 영역 스캔 [확인]

1292 sectors 전체 스캔 결과:
- **파티션 상대 섹터 12 (절대 섹터 2060)만 데이터 포함** — Windows 부트 에러 메시지
- 나머지: 전부 비어있음 (all zeros)
- 펌웨어 데이터 없음

### 9.4 MBR 갭 / 디스크 끝 스캔 [확인]

- MBR 갭 (절대 섹터 1-2047): 완전 비어있음
- 디스크 끝: 파티션이 디스크 끝까지 차지, 숨겨진 영역 없음

## 10. 디스크 이미지 문자열/패턴 탐색 [확인]

### 10.1 확인된 패턴

| 패턴 | 발견 수 | 위치 | 판정 |
|------|--------|------|------|
| `GP$322 Generalplus AviPackerV3 20140916` | 1 | AVI JUNK 청크 | [확인] 인코더 시그니처 |
| `GPEncoder` | 20+ | JPEG COM 마커 | [확인] JPEG 인코더 마킹 |
| `TCSYSDIR` | 1 | FAT 루트 디렉터리 | [확인] 카메라 펌웨어가 만든 숨김 시스템 디렉터리 (attr 0x18) |
| `GPZP` | 1 | 데이터 영역 offset 1.86GB | [추정] 엔트로피 7.90 → MJPEG 압축 내 우연 일치 가능성 높음 |
| `GPFW` | 1 | 데이터 영역 offset 142MB | [추정] 엔트로피 7.95 → 동일 사유로 우연 일치 가능성 |
| PNG 파일 다수 | 20+ | 삭제된 영역 | [확인] Android APK 잔여 데이터 (이전 SD 카드 사용 흔적) |

### 10.2 발견되지 않은 패턴

전체 3.96GB 디스크에서 아래 문자열 **미발견**:
- GP1235, GPL32080, GPCV (SoC 모델명)
- Demo, firmware, version (펌웨어 관련)
- SPRITE, DC23, SMW-DC (제품/제조사)
- ISP 파라미터, 캘리브레이션 데이터
- 삭제된 펌웨어 관련 파일

### 10.3 결론

`Demo 1.00` 문자열이 SoC의 USB String Descriptor에만 있고 SD 카드에는 없음 → 펌웨어는 SD 카드가 아닌 SoC 내부에 저장됨 [확인].

## 11. 물리 분해 결과 [확인]

### 11.1 PCB 식별

| 항목 | 값 |
|------|-----|
| PCB 모델 | **DP-5307B** |
| 인증 | RoHS |

### 11.2 앞면 (부품면)

| 위치 | 부품 | 설명 |
|------|------|------|
| 상단 | MicroSD 슬롯 | 금속 쉴드 커버 (SoC 실드가 아님) |
| 상단 우측 | B+ / B- | LiPo 배터리 커넥터 |
| 좌측 | Micro USB 포트 | 충전 + 데이터 |
| 하단 | SPK 패드 | 스피커 연결 (빨간 와이어) |
| PCB 인쇄 | 开关机 / 拍照 | 전원 스위치 / 촬영 버튼 레이블 |
| 소형 IC | USB 근처 | 충전 IC / ESD 보호 [추정] |

### 11.3 뒷면

| 위치 | 부품 | 설명 |
|------|------|------|
| 중앙 | **SoC (QFP)** | 메인 프로세서 — 마킹 아래 참조 |
| 중앙 | MEMS 마이크 | 둥근 은색, 구멍 패턴 |
| 상단 | LED | 플래시 또는 상태 표시등 |
| 우측 | FPC 케이블 | LCD 디스플레이 연결 (주황색) |

### 11.4 SoC 칩 마킹 [확인]

```
24DC          ← 로트/배치 코드 (2024년 12월 추정)
MQ44F50.1     ← 다이/내부 파트넘버
2523          ← 패키징 날짜 (2025년 23주차)
```

- 패키지: QFP (다핀)
- 제조사: Generalplus [확인] (USB VID 0x1B3F + GPEncoder/AviPacker 시그니처)
- 상용 모델명: **GP1235** [확인] (Made-in-China OEM 스펙에서 `Main Control Chip: GP1235` 직접 확인)
- 센서: **SuperPix SP1405** (1/4" CMOS, 1MP, 1280×720, DVP) — 센서 네이티브가 720p이므로 독립 촬영 1600×1200는 SoC 업스케일
- `MQ44F50` = GP1235의 다이 마킹 [확인]
- 공개 데이터시트 없음 (Generalplus 인증 벽 뒤)

### 11.5 외부 SPI 플래시: 발견! [확인]

~~이전 결론: PCB 양면에 별도 SPI 플래시 없음~~ → **정정: SPI NOR 플래시 존재 확인**

| 항목 | 값 |
|------|-----|
| 제조사 | PUYA Semiconductor (普冉半导体) |
| 모델 | **PY25D80HB** |
| 용량 | **8Mbit = 1MB** |
| 인터페이스 | SPI (W25Q80 호환) |
| 동작 전압 | 2.3V ~ 3.6V |
| 패키지 | 8-pin SOIC |
| 위치 | 뒷면, SoC 상단 |
| 날짜/로트 | 5B1PM4B |

**펌웨어는 이 칩에 저장되어 있으며, CH341A + SOIC8 클립으로 덤프/수정/재기록 가능.**

### 11.6 UART/디버그 패드 [확인]

전용 핀헤더 없음. SoC 근처에 빈 패드 2개 존재 (용도 미확인, UART TX/RX 가능성).

## 12. 버튼 조합 ISP 모드 실험 [확인]

> 목표: 웹캠/저장장치 외 제3의 USB 모드(ISP/다운로드) 존재 여부 확인

### 12.1 실험 결과

| # | SD | 조합 | 결과 |
|---|-----|------|------|
| 1 | 없음 | 复位 누른 채 연결 | 웹캠 (复位 중 전원 안 켜짐, 놓으면 부팅) |
| 2 | 없음 | 촬영 누른 채 연결 | 웹캠 |
| 3 | 없음 | 전원 누른 채 연결 | 웹캠 |
| 4 | 없음 | 复位+촬영 동시 | 웹캠 |
| 5 | 없음 | USB 중 复位 짧게 | 웹캠 (재부팅, 전환 중 동일 PID) |
| 6 | **있음** | 촬영 누른 채 연결 | **저장장치** (0x0C52) |
| 7 | **있음** | 전원 누른 채 연결 | 저장장치 |
| 8 | **있음** | 复位+촬영 동시 | 저장장치 |

### 12.2 결론 [확인]

- SD 카드 없음 → 항상 웹캠 모드 (0x1B3F:0x2002)
- SD 카드 있음 → 항상 저장장치 모드 (0x1B3F:0x0C52)
- **버튼 조합과 무관하게 SD 카드 유무가 모드를 결정**
- 제3의 ISP/다운로드 모드는 미발견
- USB 모니터링(0.5s 폴링)으로도 전환 중 다른 PID 미감지

## 13. GPFW/GPZP 바이너리 추출 검증 [확인]

### 13.1 GPFW (offset 142,448,221)

- JPEG 스트림 밖에 위치 (EOI 3,543B 전) [확인]
- 매직 직후 바이트에 **헤더 구조 없음**: 사이즈 필드, CRC, 버전 문자열, ARM vector table 모두 부재
- 엔트로피 7.12 (고엔트로피)
- **판정: 거짓 양성** — 고엔트로피 데이터(Android APK 잔여물 영역)에서 4바이트 우연 일치

### 13.2 GPZP (offset 1,858,386,799)

- **JPEG 스트림 내부** (SOI 93KB 뒤, EOI 없음) [확인]
- **판정: 거짓 양성 확정** — MJPEG 압축 데이터 내 우연 일치

### 13.3 통계적 근거

2GB 고엔트로피 데이터에서 특정 4바이트 패턴이 1회 나타날 확률 ≈ 50%. 양쪽 모두 통계적 기대 범위.

## 14. TCSYSDIR 백도어 시도 [확인]

TCSYSDIR 및 루트에 `config.txt`, `engmode.txt`, `debug.txt`, `logger.txt` 생성 후 카메라 독립 부팅 → 사진/영상 촬영 → 재연결 확인.

결과: **카메라가 모든 파일을 무시.** 새로운 로그 파일이나 반응 없음.

## 15. SD 카드 펌웨어 파일명 시도 [확인]

31개 후보 파일명으로 더미 파일(텍스트 "test") 생성 후 카메라 부팅:

```
FWDC23.bin, CARDV.bin, FWUPDATE.BIN, GP_FW.BIN, GPLUS.bin,
GP1235.bin, GPCV1235.bin, DP5307.bin, rom_sd.bin, SPHOST.BRN,
FIRMWARE.bin, FW_DC.bin, GPLUS_ext.bin, DC23.bin, DC23FW.bin,
FWDC23C.bin, MQ44F50.bin, DP5307B.bin, ISP_FW.bin, GP_ISP.bin,
update.bin, UPDATE.BIN, fwupdate.bin, cardv.bin, DEMO.bin,
demo.bin, GP322.bin, GENERALPLUS.bin, fw.bin, FW.bin, FW.BRN,
SPHOST.bin, SPI_FW.bin, FLASH.bin, GENPLUS.bin
```

결과: **부팅 시 아무 변화 없음.** LED, 화면, 부팅 시간 모두 동일.

## 16. 독립 녹음 기능 발견 [확인]

TCSYSDIR 실험 중 촬영한 새 파일에서 발견:

| 파일 | 포맷 | Sample Rate |
|------|------|------------|
| RECR0009.wav | PCM 16-bit mono | **22,050 Hz** |
| RECR0010.wav | PCM 16-bit mono | **22,050 Hz** |

SoC의 오디오 능력: 독립 녹음 22kHz > 독립 영상 16kHz > USB 웹캠 8kHz

## 17. 탐색 경로 현황 (최종)

### 17.1 소진된 경로

| 경로 | 시도 내용 | 결과 |
|------|----------|------|
| UVC 벤더 확장 | Extension Unit 탐색 | 없음 |
| USB Vendor Requests (웹캠) | 0x00~0xFF | 무응답 |
| USB Vendor Requests (저장장치) | 0x00~0xFF | 무응답 |
| SCSI Vendor Commands | 0xC0~0xFF | macOS 커널 점유 |
| SD 카드 숨겨진 영역 | MBR/예약/디스크 끝 | 비어있음 |
| SD 카드 문자열 탐색 | 3.96GB 스캔 | FW 데이터 없음 |
| GPFW/GPZP 추출 검증 | 헤더 구조 분석 | 거짓 양성 |
| 외부 SPI 플래시 | PCB 양면 확인 | 없음 |
| UART/디버그 핀헤더 | PCB 양면 확인 | 전용 핀헤더 없음 |
| 버튼 조합 ISP 모드 | 9가지 조합 | 웹캠/저장장치만 |
| TCSYSDIR 백도어 | 4종 파일 삽입 | 반응 없음 |
| SD 카드 FW 파일명 | 31개 후보 | 반응 없음 |

### 17.2 남은 경로

| 경로 | 설명 | 현실성 |
|------|------|--------|
| **소프트웨어 후처리** | 웹캠 영상 실시간 화질 보정 | 높음 (확실) |
| **렌즈 초점 조정** | 물리적 초점 최적화 | 중간 |
| **SoC 근처 빈 패드** | USB-TTL로 UART 시도 (장비 필요) | 중간 |
| **Linux SCSI 벤더 명령** | 커널 detach 후 재시도 | 낮음 |
| **커뮤니티/제조사 문의** | DP-5307B/MQ44F50.1로 검색 | 불확실 |

## 18. 분석에 사용된 도구

| 도구 | 용도 |
|------|------|
| `ioreg -r -c IOUSBHostDevice` | macOS USB 장치 트리 |
| `system_profiler SPCameraDataType` | 카메라 장치 목록 |
| `system_profiler SPAudioDataType` | 오디오 장치 목록 |
| PyUSB (`usb.core`) | USB 디스크립터 덤프, 벤더 명령 탐색 |
| ffmpeg (AVFoundation) | 비디오/오디오 캡처 |
| OpenCV (cv2) | 이미지 품질 분석 |
| Python wave/numpy | 오디오 분석 |
| `dd` + Python mmap | raw 디스크 섹터 분석, 바이너리 패턴 탐색 |
| `scripts/usb_monitor.sh` | USB 장치 변화 실시간 모니터링 |

## 19. 분석 파일 위치

```
diagnostics/mac_analysis/
├── frame_auto.jpg          # 기본 해상도 캡처 (1920×1080, 업스케일)
├── frame_1080p.jpg         # 1080p 캡처 (업스케일)
├── frame_720p.jpg          # 720p 시도 (손상 — 녹색 프레임)
├── frame_720p_v2.jpg       # 720p 재시도 (손상)
├── video_2sec.mp4          # 2초 비디오 (1920×1080, H.264)
├── audio_sample.wav        # 3초 오디오 (8kHz, 무음)
├── audio_test2.wav         # 2초 오디오 재시도 (무음)
├── disk_image.img          # 디스크 이미지 (부분, ~2GB/3.96GB)
├── mbr_gap_dump.hex        # MBR 갭 hex 덤프
└── fw_extract/
    ├── GPFW_region_5MB.bin # GPFW 주변 추출 (거짓 양성 확정)
    └── GPZP_region_5MB.bin # GPZP 주변 추출 (거짓 양성 확정)
```
