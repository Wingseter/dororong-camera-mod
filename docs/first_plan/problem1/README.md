# Problem 1: 720p Native 해상도 출력 — 업스케일링 제거

> 일시: 2026-03-29
> 상태: 미해결 — 첫 시도 brick 발생, 복구 완료
> 우선순위: 최상 (Phase 4 핵심)

## 문제

카메라가 사진 모드에서 센서 native 1280x720을 **1600x1200으로 강제 업스케일**하여 출력.
대각선 에지에 심각한 **계단 현상(staircase/aliasing)** 발생 — 현재 화질의 근본적 문제.

## 발견한 것

### 해상도 스위치 코드 (ARM)

펌웨어 내 photo resolution을 결정하는 ARM 조건 분기 코드 발견:

```
파일 오프셋 0x1FDD0~0x1FDE8:

E3500002    CMP R0, #2              ← mode 2 체크
03A04E64    MOVEQ R4, #0x640 (1600) ← mode 2: width=1600
03A05E4B    MOVEQ R5, #0x4B0 (1200) ← mode 2: height=1200
0A000004    BEQ ...
E3500003    CMP R0, #3              ← mode 3 체크
13A04FA0    MOVNE R4, #0x280 (640)  ← fallback: width=640 (VGA)
03A04E50    MOVEQ R4, #0x500 (1280) ← mode 3: width=1280 (!)
```

**mode 3에 이미 native 1280이 존재!** 하지만 카메라는 항상 mode 2 사용.

### 동일 패턴 3곳

| 위치 | 내용 | 역할 추정 |
|------|------|----------|
| 0x1C764 | MOV R4, #1600 (width only) | 버퍼 할당용? |
| 0x1C870 | MOV R0, #1600 (width only) | 버퍼 할당용? |
| 0x1FDD4/D8 | MOV R4, #1600 + MOV R5, #1200 (width+height) | **JPEG 인코더 입력** |

### 설정 블록은 무관

`+0x02` (photo resolution index)를 0x00~0x04로 변경해도 출력은 항상 1600x1200.
→ 해상도는 설정 블록이 아닌 **펌웨어 코드에 하드코딩**.

## 시도한 것

### 시도 1: ARM immediate 패치 + SD 업그레이드 (실패 → brick)

**패치 내용:**
```
0x1FDD4: 0x03A04E64 → 0x03A04C05  (MOV R4, #1600 → MOV R4, #1280)
0x1FDD8: 0x03A05E4B → 0x03A05E2D  (MOV R5, #1200 → MOV R5, #720)
0x1C764: 0x03A04E64 → 0x03A04C05  (MOV R4, #1600 → MOV R4, #1280)
0x1C870: 0x03A00E64 → 0x03A00C05  (MOV R0, #1600 → MOV R0, #1280)
```

**결과: 부팅 불가 (brick)**. CH341A로 원본 복구.

**실패 원인 후보:**

1. **GPNV XOR 체크섬 오류**
   - 코드 영역(0x01xxxx)이 GPNV XOR 범위 안인지 밖인지 불확실
   - 차분 업데이트가 잘못되었을 수 있음
   - 이전 경험: welcome(0x0AA000)은 밖, brightness(0x08279C)는 안

2. **SD 업그레이드 검증 실패**
   - SD 바이트합 체크섬은 도구가 올바르게 계산
   - 하지만 부트로더가 코드 영역 무결성을 별도 검증할 가능성

3. **버퍼 크기 불일치**
   - 0x1C764/0x1C870이 버퍼 할당용이라면, 1600→1280 변경 시
     다른 곳에서 여전히 1600x1200 버퍼를 기대하여 메모리 오류

4. **ARM 인코딩 오류**
   - 1280 = 0x500 → imm8=5, rotate=12 → 0xC05 ← 검증 필요
   - 720 = 0x2D0 → imm8=0x2D, rotate=14 → 0xE2D ← 검증 필요

## 다음 접근법

### 접근 A: CH341A 직접 쓰기 (SD 우회)

SD 업그레이드 대신 CH341A로 패치된 펌웨어를 직접 SPI에 쓰기.
→ SD 바이트합/빌드문자열 검증 완전 우회
→ GPNV XOR은 부트로더 복구(`GPNVBtLdr Recover`)에 맡김

**최소 패치**: 0x1FDD4/0x1FDD8 2곳만 (width+height 쌍)

### 접근 B: mode 3 강제 선택

mode 2 → mode 3으로 전환하면 기존 코드의 1280을 그대로 사용 가능.
R0에 로드되는 모드 값을 찾아서 2→3으로 변경.
→ 코드 자체를 수정하는 대신 **모드 선택 분기만 변경**

### 접근 C: 720p 출력 검증 (Ghidra 심층 분석)

패치 전에 Ghidra에서 전체 경로를 추적:
1. R0(모드값)은 어디서 오는가?
2. R4/R5(width/height)는 어디에 전달되는가?
3. JPEG 인코더 함수(~0x055820)의 파라미터 구조
4. 버퍼 할당이 R4/R5와 연동되는지
5. 720 높이가 JPEG 타임스탬프 오버레이와 충돌하지 않는지

### 접근 D: JPEG 후처리 (최후 수단)

펌웨어 수정 대신, 촬영된 1600x1200 JPEG을 **호스트에서 720p로 다운스케일**.
→ 근본 해결은 아니지만 계단 현상은 제거됨

## 도구

- `scripts/settings_patch.py --raw-patch` — 펌웨어 코드 바이트 패치 (구현 완료)
- `E:\Kwon\Utility\flashrom-1.4\flashrom.exe` — CH341A SPI 프로그래머
- Ghidra 프로젝트: `analysis/ghidra_project/GP1235_FW.gpr`

## 관련 파일

- `analysis/GP1235_firmware.bin` — 원본 펌웨어
- `analysis/GP1235_phase3.bin` — Phase 3 기반 (Q-테이블 + 브랜딩)
- `diagnostics/mac_analysis/firmware_backup_1.bin` — SPI 덤프 원본 (복구용)
