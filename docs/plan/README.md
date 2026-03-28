# DC23 프로젝트 — 진행 계획

> 최종 갱신: 2026-03-22
> 상태: Phase 0~1 실험 완료 → Phase 2 (소프트웨어 개선) 진입
> 참고: Codex/Gemini 의견 반영 완료

## 현재 상태 요약

### 확정된 사실

| 항목 | 값 |
|------|-----|
| 제품 | SMW-DC23C / DC23 (SPRITE GROUP LIMITED) |
| SoC | Generalplus **GP1235** (다이 마킹 `MQ44F50.1`, Made-in-China OEM 스펙에서 확정) |
| 센서 | **SuperPix SP1405** (1/4" CMOS, 1MP, 1280×720, DVP 인터페이스) |
| SPI Flash | **PUYA PY25D80HB** (8Mbit/1MB, SPI NOR, W25Q80 호환, 2.3~3.6V) |
| PCB | DP-5307B |
| 펌웨어 버전 문자열 | `Demo 1.00` (USB String #3, 웹캠 모드 한정) |
| 펌웨어 빌드 | `5307 20260129` (2026-01-29) |
| SD 업그레이드 파일명 | **`JH_5307*.bin`** (펌웨어 바이너리에서 직접 추출) |
| 웹캠 출력 | 1280×720, MJPEG, 30fps 고정, Brightness만 조정 가능 |
| 독립 촬영 | 사진 1600×1200 / 영상 1280×720 MJPG + PCM 16kHz mono |
| 독립 음성 녹음 | WAV 22,050 Hz 16-bit mono |
| USB 모드 결정 | SD 카드 유무로 결정 (있음→저장장치, 없음→웹캠) |
| 외부 SPI 플래시 | **PUYA PY25D80HB** (8Mbit/1MB, SPI NOR, W25Q80 호환) |
| UART/디버그 패드 | 전용 핀헤더 없음. SoC 근처 빈 패드 2개 존재 (용도 미확인) |
| ISP/다운로드 모드 | 버튼 조합 9가지 시도 → 미발견 |

### 완료된 실험 (Phase 0~1)

| 실험 | 결과 | 상세 |
|------|------|------|
| **버튼 조합 ISP 모드** (9가지) | **미발견** | SD 유무가 모드 결정. 버튼과 무관 |
| **GPFW/GPZP 바이너리 추출** | **거짓 양성** | GPZP=JPEG 내부, GPFW=헤더 구조 없음 |
| **TCSYSDIR 백도어** | **반응 없음** | config/debug/engmode/logger 파일 무시됨 |
| **SD 카드 FW 파일명** (31개) | **반응 없음** | 부팅 시 아무 변화 없음 |
| **USB Vendor Requests** (양쪽 모드) | **무응답** | macOS 한정, 0x00~0xFF 전수 |
| **SD 카드 숨겨진 영역** | **비어있음** | MBR 갭, 예약 영역, 디스크 끝 |
| **디스크 문자열 탐색** | **FW 관련 없음** | GP 모델명, 펌웨어 문자열 모두 미발견 |

### 버튼 조합 실험 상세

| # | SD | 조합 | 결과 |
|---|-----|------|------|
| 1 | 없음 | 复位 누른 채 연결 | 웹캠 (복위 중 전원 안 켜짐, 놓으면 부팅) |
| 2 | 없음 | 촬영 누른 채 연결 | 웹캠 |
| 3 | 없음 | 전원 누른 채 연결 | 웹캠 |
| 4 | 없음 | 复位+촬영 동시 | 웹캠 |
| 5 | 없음 | USB 중 复位 짧게 | 웹캠 (재부팅, 전환 중 동일 PID만) |
| 6 | **있음** | 촬영 누른 채 연결 | **저장장치** |
| 7 | **있음** | 전원 누른 채 연결 | 저장장치 |
| 8 | **있음** | 复位+촬영 동시 | 저장장치 |

**결론**: SD 카드 없음 → 항상 웹캠(0x2002) / SD 카드 있음 → 항상 저장장치(0x0C52). 제3의 모드 없음.

### 소진된 경로

| 경로 | 시도 내용 | 결과 |
|------|----------|------|
| UVC Extension Unit | 디스크립터 확인 | 없음 |
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
| SD 카드 FW 파일명 | 42개 후보 | 반응 없음 (정답은 `JH_5307*.bin` — 펌웨어 덤프 후 발견) |

## 앞으로의 계획

### Phase 2: SPI 플래시 펌웨어 덤프 및 분석 [장비 도착 대기]

> SPI 플래시(PUYA PY25D80HB) 발견으로 펌웨어 직접 접근 가능해짐

**구매 완료 장비:**
- [x] CH341A 프로그래머 풀세트 (SOP8/SOP16 클립, 1.8V 어댑터 포함)
- [x] CP2102 USB-TTL 어댑터 (3.3V/5V)
- [x] ANENG A830L 디지털 멀티미터
- [x] T12 인두 스테이션

**보유 장비:**
- [x] 브레드보드
- [x] 점퍼 와이어

#### 2-0. 안전 검증 [카메라 연결 전에 반드시]

- [ ] CH341A를 3.3V 점퍼로 설정
- [ ] CH341A를 PC에만 연결 (카메라 미연결)
- [ ] 멀티미터로 VCC 핀 전압 측정 → 3.3V 확인
- [ ] 멀티미터로 데이터 핀 (CLK/MOSI/CS) 전압 측정 → 5V면 안전 조치 필요
- [ ] 인두로 배터리 와이어 한쪽 분리 (SoC 간섭 방지)

#### 2-1. 펌웨어 백업 (덤프) [최우선]

- [ ] CH341A + SOIC8 클립으로 PY25D80HB 연결
- [ ] `flashrom` 또는 CH341A 소프트웨어로 1MB 전체 덤프
- [ ] `firmware_backup.bin` 저장 (원본 보존, 절대 수정 금지)
- [ ] 2회 덤프 후 MD5/SHA256 비교 (읽기 안정성 확인)

#### 2-2. 펌웨어 분석

- [ ] Ghidra로 ARM 바이너리 분석
- [ ] 문자열 탐색 ("Demo 1.00", "GPEncoder", "GENERAL" 등)
- [ ] ISP 파라미터 테이블 찾기 (밝기, 샤프닝, WB, 노출 기본값)
- [ ] UVC 디스크립터 위치 찾기 (Brightness 기본값 16)
- [ ] 메모리 맵 / 부트 시퀀스 파악

#### 2-3. 펌웨어 수정 및 재기록

- [ ] 파라미터 수정 (예: Brightness 기본값 16 → 128)
- [ ] `firmware_modified.bin` 생성
- [ ] CH341A로 수정된 펌웨어 쓰기
- [ ] 동작 검증
- [ ] 실패 시 `firmware_backup.bin`으로 원복

#### 2-4. UART 탐색 (병행)

- [ ] 멀티미터로 SoC 근처 빈 패드 2개 전압 측정
- [ ] UART TX 판별 (전압 흔들림 확인)
- [ ] CP2102로 UART 로그 캡처 시도

### Phase 3: 고급 목표

| 경로 | 설명 | 현실성 |
|------|------|--------|
| SoC 리버스 엔지니어링 | 펌웨어 바이너리에서 ARM 코드 분석, 메모리맵/GPIO 파악 | 중간 |
| SD 카드 자동 업데이트 추가 | 펌웨어에 SD→SPI 자동 플래싱 루틴 삽입 (이후 CH341A 불필요) | 중간 |
| 커스텀 펌웨어 작성 | LCD 드라이버, 버튼 GPIO 제어 | 높은 난이도 |
| DOOM 포팅 | ARM 코어 + LCD + 버튼 + SD 카드로 WAD 로드 | 극한 도전 |

## 하드웨어 구성도

```
SP1405 (1MP CMOS) ──DVP──→ GP1235 (ARM SoC, MQ44F50.1)
                              ├──SPI──→ PY25D80HB (1MB 펌웨어)
                              ├──USB──→ PC (UVC/Mass Storage)
                              ├──FPC──→ LCD (0.96" IPS, 80×160)
                              ├──SD───→ MicroSD (FAT32, 최대 128GB)
                              ├──────→ MEMS Microphone
                              ├──────→ Speaker (SPK)
                              ├──────→ LED Flash (闪光灯)
                              └──────→ Buttons (电源/拍照/复位)
```

### 가장 강한 추적 키 (검색/문의 시)

`MQ44F50.1` > `DP-5307B` > `Demo 1.00` > `1B3F:2002` / `1B3F:0C52` > `DC23`

## 참고 자료

- [Windows 분석 보고서](../windows_report.md)
- [macOS 분석 보고서](../mac_analysis_report.md)
- [Codex 의견 - 펌웨어 경로](../idea/codex/firmware_next_steps_without_clips_2026-03-22.md)
- [Codex 의견 - 부트모드 실험표](../idea/codex/boot_mode_experiment_matrix_2026-03-22.md)
- [Gemini 의견](../idea/gemini/firmware_analysis_next_steps.md)
- [Sprite Group 공식](https://www.spritegroup.com/en/)
- [DC23 TVCMall 스펙](https://www.tvcmall.com/details/dc23-mini-digital-camera-0-96-inch-screen-portable-ccd-hd-video-recorder-for-students-black-sku6857000119b.html)
- [808 Camera #9 리뷰](https://chucklohr.com/808/C9/)
- [808 MicroCam 펌웨어 위키](https://github.com/mandl/808MicroCam/wiki/808-Micro-Camera-Firmware)
- [GPCV1248 분해 사례](https://mastercircuits.blogspot.com/2017/06/gpcv1248-action-camera-teardown.html)
- [GoPrawn Generalplus 포럼](https://www.goprawn.com/forum/others/101-generalplus-socs-datasheets)
