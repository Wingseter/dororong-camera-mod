# GENERAL-UVC / DC23 현재 상황 정리

## 1. 현재까지 가장 강한 제품 식별

- 현재 가장 유력한 제품 축은 `SMW-DC23C / DC23` 계열임
- 제조사 표기: `SPRITE GROUP LIMITED`
- 전자파 적합등록: `R-R-sMW-SMW-DC23C`
- 배터리 제조사: `SHENZHEN MITACBATTERY TECHNOLOGY.CO.LTD`
- 배터리 KC 인증: `XU102612-21001J`
- 파생 모델명: `402030`
- 디스플레이: `0.96 IPS LCD`
- 동영상 표기 스펙: `720p`
- 사진 표기 스펙: `최대 200만 화소`

## 2. 로컬에서 직접 확인한 장치 정보

### USB 식별

- 웹캠 모드 장치명: `GENERAL - UVC`
- 웹캠 모드 장치 ID: `USB\VID_1B3F&PID_2002&REV_0100&MI_00`
- 오디오 인터페이스 존재:
  - `GENERAL - AUDIO`
  - `USB\VID_1B3F&PID_2002&MI_02`
- 저장장치 모드 관련 ID:
  - `USB\VID_1B3F&PID_0C52`
- Windows 기본 드라이버 사용:
  - 비디오: `usbvideo.inf`
  - 오디오: `usbaudio`

### 저장장치 모드 디스크 정보

- 디스크 벤더명: `GENPLUS USB-MSDC DISK A` (직접 확인)
- 디스크 펌웨어 버전: `1.00` (직접 확인)
- 파티션: 1개, 약 3.7GB
- 숨겨진 파티션: **없음** (PowerShell Get-Partition으로 확인)
- 숨겨진 파일: **없음** (dir /a:h /s로 확인)
- BIOS 디바이스 경로: `\_SB.PCI0.GP13.XHC0.RHUB.PRT2`

## 3. 저장장치 모드에서 확인한 파일

- 이동식 드라이브: `H:`
- 볼륨 레이블: `SD`
- 파일시스템: `FAT32`
- `time.txt` 내용:

```text
2025-01-01 23:59:59
```

- 독립 촬영 샘플 파일:

| 파일명 | 크기 | 날짜 |
|--------|------|------|
| `PICT0001.jpg` | 172,794 bytes | 2025-02-21 |
| `PICT0002.jpg` | 232,533 bytes | 2025-02-21 |
| `PICT0003.jpg` | 306,638 bytes | 2025-02-21 |
| `PICT0004.jpg` | 207,858 bytes | 2025-02-21 |
| `PICT0005.jpg` | 120,690 bytes | 2025-02-21 |
| `PICT0006.jpg` | 152,259 bytes | 2025-02-21 |
| `MOVI0007.avi` | 15,995,904 bytes | 2025-02-21 |

## 4. 미디어 파일에서 직접 확인한 값

### 사진 (직접 검증 완료)

- `PICT0006.jpg` 실측 해상도: `1600x1200`, RGB, 8bit
- EXIF 데이터: **없음** (PIL `_getexif()` → None)
- JPEG 내부 구조: `SOI` → `SOF0(1600x1200)` → `COM(GPEncoder)` → `DQT` → `DHT` → `SOS`
- 타임스탬프: 좌하단에 노란색으로 오버레이 (예: `2025/02/21 05:51:56`)

### 영상 (직접 검증 완료)

- `MOVI0007.avi` 길이: 약 `9초`
- 비디오:
  - `1280x720`
  - `MJPG` (mjpg fourcc)
  - `30fps`
  - 셸 메타데이터 기준 약 `13.45 Mbps`
- 오디오 스트림:
  - `PCM`
  - `16kHz`
  - `mono`
  - `16-bit`
  - 대략 `256 kbps`
- AVI 내부 시그니처 (바이너리에서 직접 확인):
  - `GP$322 Generalplus AviPackerV3 20140916`
  - `GPEncoder`

## 5. 칩셋 정보에 대한 현재 판단

현재 칩셋에 대해 두 개의 축이 존재함.

### A. 기존 커뮤니티 / 외부 분석 축

- `Generalplus GPL32080A`
- `808 Camera #9` 계열
- `VID_1B3F:PID_2002` / `VID_1B3F:PID_0C52`
- 출처: [chucklohr.com 808 #9 리뷰](https://chucklohr.com/808/C9/), [Device Hunt](https://devicehunt.com/view/type/usb/vendor/1B3F/device/2002)

### B. 현재 제품 페이지 / 사용자 확인 축

- `DC23`
- 제조사 `SPRITE GROUP LIMITED`
- 제품 페이지 사양상 칩셋 `GP1235` (TVCMall 스펙시트 기준)
- 센서 `SP1405 1MP`
- `Real 720P`, `Photo 2MP`, `0.96 IPS LCD`
- 출처: [TVCMall DC23 스펙](https://www.tvcmall.com/details/dc23-mini-digital-camera-0-96-inch-screen-portable-ccd-hd-video-recorder-for-students-black-sku6857000119b.html)

### 현재 결론

- `Generalplus` 계열인 것은 매우 유력함
- `GPEncoder` 와 `Generalplus AviPackerV3` 가 바이너리에서 직접 확인됨
- 다만 정확한 SoC를 `GPL32080A` 로 확정하기에는 최신 제품 정보와 충돌함
- 현재는 `DC23 / GP1235 가능성`이 더 실사용 제품 정보에 가까움
- 따라서 `GPL32080A 확정`으로 전제하고 펌웨어를 섣불리 적용하면 위험함
- **정확한 칩셋은 분해 후 보드 마킹으로 최종 확인 필요**

## 6. 초기 가설과 현재 가설의 차이

### 초기 가설

- `Generalplus 기반 808 Camera #9 또는 유사 클론`

### 현재 더 강한 가설

- `SPRITE GROUP LIMITED`가 유통/제조하는 `DC23` 계열 신형 키링 카메라
- 내부 인코더는 `Generalplus` 계열
- 독립 촬영 실제 출력은 `1600x1200 JPG`, `1280x720 MJPG AVI`

## 7. 웹캠 모드 화질 진단 (2026-03-21 직접 측정)

### 기본 상태 (밝기 16/255)

| 항목 | 값 |
|------|-----|
| 해상도 | 1280x720 (고정, 변경 불가) |
| 선명도 (Laplacian variance) | **9.08** (매우 흐림) |
| 평균 밝기 | 55.65 (매우 어두움) |
| 동적 범위 | 6~185 (좁음) |

### 밝기 조정 후 (밝기 128/255)

| 항목 | 값 |
|------|-----|
| 선명도 (Laplacian variance) | **169.8** (대폭 개선) |
| 평균 밝기 | 111.3 (정상) |
| 동적 범위 | 0~255 (정상) |

### UVC 컨트롤 지원 현황

| 컨트롤 | 지원 | 값 |
|--------|------|-----|
| Brightness | **O** | 16 (조정 가능: 0~255) |
| Contrast | X | -1 |
| Saturation | X | -1 |
| Hue | X | -1 |
| Gain | X | -1 |
| Exposure | X | -1 |
| Sharpness | X | -1 |
| Gamma | X | -1 |
| White Balance | X | -1 |
| Auto Exposure | X | -1 |
| Auto WB | X | -1 |
| Zoom / Focus / Autofocus | X | -1 |

**Brightness만 유일하게 조정 가능**. 나머지 ISP 파라미터는 UVC를 통해 접근 불가.

### 소프트웨어 후처리 파이프라인 (테스트 완료)

1. 밝기 조정 (128/255) → 선명도 9 → 170
2. Bilateral Filter 디노이징 (에지 보존)
3. Gray World 화이트밸런스 보정 (녹색 색조 제거)
4. CLAHE 대비 보정 (clipLimit=1.5)
5. Unsharp Mask 샤프닝 (amount=0.5, sigma=2.0)
6. 감마 보정 (gamma=0.9)

결과: 선명도 **9 → 170 → 302**, 색조 보정됨, 노이즈 감소

## 8. 화질 개선 관점의 현재 판단

- 사용자는 극적인 화질 향상은 기대하지 않음
- 현재 현실적인 개선 여지는 아래 범위로 판단됨:
  1. JPEG/MJPEG 압축률
  2. 샤프닝
  3. 노이즈 리덕션
  4. 자동 노출 / 화이트밸런스
  5. 렌즈 초점

- 해상도 자체를 큰 폭으로 높이는 개선 가능성은 낮음
- 사진/영상이 이미 `1600x1200 / 1280x720`로 나오는 점을 보면, 숨겨진 고성능 모드가 있을 확률은 낮음
- 전체적으로 흐리면 펌웨어보다 렌즈 초점 문제 가능성이 큼
- **웹캠 모드의 밝기 기본값이 16/255로 극히 낮게 설정된 것이 화질 저하의 주요 원인 중 하나** (직접 확인)

## 9. 펌웨어 확보 가능성에 대한 현재 결론

### 현재까지 확인한 것

- 공개 웹 검색으로 `SMW-DC23C / DC23 / SPRITE GROUP LIMITED`용 공식 펌웨어 다운로드 링크는 찾지 못함
- 구형 `808 #9` 계열 자료는 많이 존재하지만, 현재 장치와 정확히 맞는 전용 펌웨어 이미지는 확인하지 못함
- 따라서 지금 시점에서 `웹에서 바로 받는 안전한 펌웨어 파일`은 확보하지 못한 상태임

### 검색 시도 상세

| 검색 대상 | 결과 |
|-----------|------|
| GP1235 데이터시트 | 비공개 |
| GPL32080A 데이터시트 | 비공개 |
| 808 #9 커뮤니티 펌웨어 | SPCA1527 기반만 존재, GP 계열 없음 |
| SD 카드 기반 펌웨어 업데이트 파일명 규칙 | 알려지지 않음 |
| Generalplus 공식 다운로드 | 인증 벽 뒤 (gpsales@generalplus.com) |
| GPZP 펌웨어 압축 포맷 | 미해독 (매직 바이트 `GPZP`) |
| Sprite Group 펌웨어 | 공식 사이트에 다운로드 없음 |
| SD 카드에서 펌웨어 흔적 | 없음 (숨김 파일/파티션 모두 확인) |

### 그렇다고 방법이 아예 없는 것은 아님

가능한 경로는 아래 세 가지임.

1. 제조/유통 채널에 직접 요청
2. 박스 / 설명서 / QR / 메뉴의 버전 정보 추적
3. 장치에서 직접 추출
   - USB vendor-specific 접근
   - SPI flash dump
   - UART

### 현재 우선순위

1. `SMW-DC23C / DC23 / SPRITE GROUP LIMITED` 축으로 공식 또는 판매 채널 문의
2. 본체 분해 후 메인 칩 / 센서 / 플래시 확인
3. 외부 플래시가 있으면 펌웨어 덤프 시도

## 10. 현재까지 만든 도구

- 장치 정보 수집 스크립트:
  - [collect-general-uvc-info.ps1](E:\Workspace\2026\dororong\collect-general-uvc-info.ps1)
- 미디어 시그니처 확인 스크립트:
  - [analyze-generalplus-media.ps1](E:\Workspace\2026\dororong\analyze-generalplus-media.ps1)
- 웹캠 모드 진단 결과 폴더:
  - [diagnostics\20260321-212028](E:\Workspace\2026\dororong\diagnostics\20260321-212028)
- 화질 테스트 이미지:
  - `test_capture.jpg` - 최초 캡처 (밝기 16, 매우 어두움)
  - `test_bright.jpg` - 밝기 255 적용
  - `step0_original.jpg` ~ `step4_final.jpg` - 후처리 단계별
  - `enhanced_v2.jpg` - 개선된 파이프라인 최종
  - `comparison.jpg` - 원본 vs 개선 비교

## 11. macOS 웹캠 모드 확인 결과 (2026-03-21 직접 확인)

Windows에서 확인한 `VID_1B3F:PID_2002` 가 macOS에서도 동일하게 잡혔다.

### IOKit / IORegistry 기준 직접 확인

- 장치명: `GENERAL - UVC`
- 제조사 문자열: `GENERAL`
- `idVendor = 6975 = 0x1B3F`
- `idProduct = 8194 = 0x2002`
- `bcdDevice = 256 = 0x0100`
- `bcdUSB = 512 = 0x0200`
- 링크 속도: `480000000` (`USB 2.0 High-Speed`)
- 버스 전력 할당: `200mA`

### 장치 시그니처 해석

macOS `ioreg` 의 `UsbDeviceSignature`:

```text
3f1b 0220 0001 ef0201 0e0100 0e0200 010100 010200
```

해석:

- `3f1b` → `VID 1B3F`
- `0220` → `PID 2002`
- `0001` → `bcdDevice 1.00`
- `ef 02 01` → Composite / IAD 계열 장치 클래스
- `0e 01 00` → Interface 0 = UVC Video Control
- `0e 02 00` → Interface 1 = UVC Video Streaming
- `01 01 00` → Interface 2 = USB Audio Control
- `01 02 00` → Interface 3 = USB Audio Streaming

즉 macOS에서도 이 장치는 **표준 UVC + 표준 USB Audio 합성 장치**로 식별된다.

### 인터페이스 소유 프로세스

- 비디오 인터페이스(0, 1): `UVCAssistant`
- 오디오 인터페이스(2, 3): `usbaudiod`

직접 확인한 인터페이스 문자열:

- `GENERAL - UVC`
- `GENERAL - AUDIO`

### 현재 모드에서 확인한 한계

- 웹캠 모드에서는 **vendor-specific 인터페이스가 보이지 않음**
- `/Volumes` 아래에 외부 볼륨이 생성되지 않아 **저장장치 모드가 아님**
- 따라서 현재 연결 상태만으로는:
  - SD 카드 파일시스템 확인
  - `time.txt` 재검증
  - 저장장치 PID `0x0C52` 확인
  - 펌웨어 파일 흔적 탐색
  - 대용량 저장장치 쪽 컨트롤러 문자열 재검증
  를 진행할 수 없음

### macOS 쪽에서 추가로 강해진 결론

- Windows와 macOS가 **동일한 USB 정체성**(`1B3F:2002`)을 독립적으로 보여줌
- 웹캠 모드의 USB 구성은 **일반적인 UVC/UAC 조합**이며 숨은 특수 인터페이스가 최소한 표면상으로는 보이지 않음
- 따라서 펌웨어 추출/업데이트 경로가 있다면 웹캠 모드보다는 아래 가능성이 더 큼:
  1. 저장장치 모드 (`1B3F:0C52`)
  2. 보드 상 SPI flash
  3. UART / 테스트패드

### 다음으로 의미 있는 단계

가장 정보량이 큰 다음 단계는 **저장장치 모드로 다시 연결해서 macOS에서 디스크/볼륨/파일 구조를 직접 확인하는 것**이다.

## 12. macOS 저장장치 모드 확인 결과 (2026-03-21 직접 확인)

저장장치 모드로 전환하자 macOS에서도 Windows에서 봤던 `VID_1B3F:PID_0C52` 축이 독립적으로 확인됐다.

### USB / 디스크 식별

- USB 장치명: `Generic USB Mass Storage Device`
- USB 제조사 문자열: `Generic USB Mass Storage Device`
- `idVendor = 6975 = 0x1B3F`
- `idProduct = 3154 = 0x0C52`
- `bcdDevice = 256 = 0x0100`
- 링크 속도: `480000000` (`USB 2.0 High-Speed`)
- 버스 전력 할당: `200mA`

### 저장장치 계층에서 확인된 이름

macOS `diskutil` / `IOMedia` 기준:

- Whole disk media name: `USB-MSDC DISK A`
- IOMedia name: `GENPLUS USB-MSDC DISK A Media`

즉 USB 문자열은 generic 하게 잡히지만, **저장장치 계층에서는 `GENPLUS USB-MSDC DISK A` 식별자가 그대로 보인다.**
이는 Windows에서 확인한 `GENPLUS USB-MSDC DISK A` 와 일치한다.

### 파티션 구조

`diskutil list /dev/disk4` 기준:

- 전체 디스크: 약 `4.0 GB`
- 파티션 스킴: `FDisk_partition_scheme`
- 파티션 수: `1개`
- 파티션 타입: `Windows_FAT_32`
- 볼륨명: `SD`

`diskutil info /dev/disk4s1` 기준:

- 마운트 위치: `/Volumes/SD`
- 파일시스템: `MS-DOS FAT32`
- 파티션 오프셋: `1,048,576 bytes` (`2048` 섹터)
- 볼륨 총 크기: `3,955,757,056 bytes`
- 사용량: 약 `17.3 MB`
- 여유 공간: 약 `3.94 GB`
- 할당 블록 크기: `4096 bytes`

현재 macOS 인식 기준으로는 **추가 파티션이 보이지 않는다.**

### 볼륨 내부 파일

루트:

- `DCIM/`
- `System Volume Information/`
- `time.txt`

`time.txt` 내용:

```text
2025-01-01 23:59:59
```

`DCIM/` 내부 파일:

- `PICT0001.jpg` `172,794 bytes`
- `PICT0002.jpg` `232,533 bytes`
- `PICT0003.jpg` `306,638 bytes`
- `PICT0004.jpg` `207,858 bytes`
- `PICT0005.jpg` `120,690 bytes`
- `PICT0006.jpg` `152,259 bytes`
- `MOVI0007.avi` `15,995,904 bytes`

즉 Windows에서 기록한 파일명 / 크기 / 시간축과 macOS에서 다시 본 값이 일치한다.

### macOS가 추가한 흔적

- `.fseventsd/`

이 디렉터리는 macOS가 볼륨을 마운트하면서 만든 것으로 보이며, 장치 원본 컨텐츠로 보지 않는 것이 맞다.

### 파일 타입 직접 확인

`file` 명령 결과:

- `PICT0006.jpg` → `JPEG image data, comment: "GPEncoder"`
- `MOVI0007.avi` → `AVI, 1280x720, 30fps, Motion JPEG, PCM mono 16000 Hz`

즉 Windows에서 확인했던 `GPEncoder` / `MJPG 720p / 16kHz mono PCM` 축이 macOS에서도 독립적으로 재현된다.

### macOS 저장장치 모드에서 강해진 결론

- `VID_1B3F:PID_0C52` 저장장치 모드가 macOS에서도 동일하게 확인됨
- 저장장치 계층 이름 `GENPLUS USB-MSDC DISK A` 가 다시 확인됨
- 파티션 구조는 현재 보이는 범위에서 `MBR(FDisk)` + `FAT32 1개` 구성
- 파일셋과 `time.txt` 값이 Windows 분석과 일치함
- 따라서 현재까지의 장치 동일성은 매우 높고, **웹캠 모드와 저장장치 모드가 같은 계열 장치라는 점은 사실상 확정적**

## 13. 다음에 하면 좋은 작업

1. 박스 앞/뒤 전체 사진 확보
2. 설명서 전체 사진 확보
3. 메뉴의 `Version`, `About`, `PC Camera`, `Mass Storage`, `OTG`, `Filter` 항목 사진 확보
4. 본체 분해
5. PCB 앞/뒤 사진 확보
6. 메인 칩 마킹 확인
7. 센서 마킹 확인
8. 외부 SPI 플래시 존재 여부 확인

## 14. 분해 시 체크 포인트

- 렌즈는 바로 돌리지 말 것
- 현재 렌즈 위치를 먼저 촬영할 것
- 고정 글루 여부 확인
- 배터리 배선과 플렉스 케이블 상태를 먼저 촬영할 것
- `25Qxx`, `W25Qxx`, `25Lxx`, `PN25Lxx` 같은 8핀 플래시가 있으면 매우 중요

## 15. 참고 자료

- [Sprite Group 공식](https://www.spritegroup.com/en/) - OEM 문의: michelle@sprite-ele.com
- [DC23 TVCMall 스펙](https://www.tvcmall.com/details/dc23-mini-digital-camera-0-96-inch-screen-portable-ccd-hd-video-recorder-for-students-black-sku6857000119b.html)
- [808 Camera #9 리뷰 - Chuck Lohr](https://chucklohr.com/808/C9/)
- [808 MicroCam 오픈소스 펌웨어 - GitHub](https://github.com/mandl/808MicroCam/wiki/808-Micro-Camera-Firmware)
- [VID_1B3F PID_2002 - Device Hunt](https://devicehunt.com/view/type/usb/vendor/1B3F/device/2002)
- [Generalplus 다운로드 (인증 필요)](https://www.generalplus.com/1LVlangLNo2SVw7SNservice_n_support_d)
- [GPCV1248 분해 사례](https://mastercircuits.blogspot.com/2017/06/gpcv1248-action-camera-teardown.html)

## 16. macOS 심층 분석 결과 (2026-03-21 추가)

> 상세 보고서: [mac_analysis_report.md](mac_analysis_report.md)

### 핵심 신규 발견

1. **펌웨어 버전: `Demo 1.00`** (USB String Descriptor #3)
   - Generalplus SDK의 **데모/평가 펌웨어**를 그대로 사용 중
   - OEM(Sprite Group)이 SDK 기본 펌웨어를 커스터마이징하지 않았을 가능성
   - 이것이 제한적 UVC 컨트롤과 낮은 기본 밝기의 근본 원인일 수 있음

2. **UVC 디스크립터 완전 디코딩**
   - UVC 1.00, Clock 6MHz
   - Camera Terminal Controls: **0x0000** (완전 비활성)
   - Processing Unit Controls: **0x0001** (Brightness만)
   - Extension Unit: **없음** (벤더 확장 제어 불가)
   - Color Profile: **(0,0,0)** (완전 미지정)

3. **Still Image Capture Method 2 + Hardware Trigger 지원**
   - UVC 프로토콜로 스틸 캡처 가능하지만 해상도는 1280×720으로 제한

4. **USB 오디오: 8kHz** (독립 녹화 16kHz의 절반)
   - Audio Feature Unit에서 Mute + Volume 제어 가능
   - macOS 캡처 테스트 결과 완전 무음 (Mute 상태 추정)

5. **macOS AVFoundation 동작**
   - 네이티브 720p 직접 제공 실패 → 1920×1080 업스케일만 정상 동작
   - 업스케일 확인: Laplacian ratio 0.64 (확실한 업스케일)
   - macOS 기본 캡처가 Windows보다 현저히 양호 (밝기 125 vs 56, 색균형 정상)

6. **Vendor-Specific USB 명령: 웹캠 모드에서 응답 없음**
   - bRequest 0x00~0x1F, 0x80~0x85, 0xFE~0xFF 모두 무응답
   - 벤더 명령은 저장장치 모드(PID 0x0C52)에서만 동작할 가능성

## 17. 현재 기준의 최종 요약

- 이 장치는 `Generalplus` 계열 인코더를 쓰는 것은 거의 확실함
  - `GPEncoder` (JPEG COM), `Generalplus AviPackerV3 20140916` (AVI JUNK chunk) 직접 확인
- 하지만 구형 `808 #9`로 단정하기보다는 `DC23` 계열 신형 제품으로 보는 것이 현재는 더 정확함
- **펌웨어: `Demo 1.00`** — Generalplus SDK 데모 펌웨어 사용 확인 (USB String #3)
- 공개 펌웨어는 아직 확보하지 못함
- 펌웨어를 얻으려면:
  - 제조/판매 채널 문의
  - 설명서/QR 추적
  - 직접 덤프
  중 하나로 가야 함
- 화질 개선은 가능하더라도 제한적일 가능성이 높음
- 웹캠 모드 밝기 기본값(16/255)이 화질 저하의 주요 원인 중 하나임이 확인됨 (macOS에서는 자동 보정)
- UVC를 통한 ISP 제어는 **불가능** (Camera Terminal=0x0000, Extension Unit 없음)
- **다음 단계**: raw 섹터/MBR 직접 덤프 가능 여부 확인 또는 분해 후 칩/센서/플래시 식별
