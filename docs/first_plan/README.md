# DC23 카메라 화질 개선 프로젝트 — 1차 계획

> 일시: 2026-03-29
> 대상: Generalplus GP1235 기반 DC23 미니 카메라
> 전제: SD 카드 업그레이드 동작 확인 완료 (펌웨어 수정 → SD → 카메라 플래시)

## 목표

**카메라 내부 펌웨어 튜닝만으로 달성 가능한 최대 화질 개선**

호스트 후처리나 AI 복원이 아닌, **카메라 자체가 더 좋은 결과물을 내도록** 만드는 것이 목표.

### 핵심 원칙 (codex 연구 반영)

1. **큰 숫자 해상도를 버리고 native 품질을 찾는다** — 1080P/12M은 720p 업스케일 추정, 진짜 디테일이 있는 모드를 우선
2. **단일 만능 세팅이 아닌 장면별 프리셋으로 간다** — Daylight/Indoor/Night/Motion 분리
3. **ISP 파이프라인 전체를 함께 튜닝한다** — AE/AWB/Gamma/CCM/Denoise/Sharpen/JPEG를 연동 조정
4. **측정 기반 반복 튜닝** — 감이 아니라 실제 촬영 결과로 점수화

### 현재 문제점

- 웹캠 밝기 기본값 16/255 → 극도로 어두움
- UVC 컨트롤 Brightness 1개만 활성화 → 호스트에서 조정 불가
- JPEG 압축이 과도하게 강함 → 블록 노이즈
- 1080P가 720p 업스케일 → 오히려 화질 저하
- 과도한 샤프닝 → 가장자리 halo/ringing
- 색상/노출/감마 등 ISP 파라미터가 공장 기본값 상태

## 하드웨어 제약

| 항목 | 값 | 비고 |
|------|------|------|
| SoC | GP1235 (ARM7TDMI ~144MHz) | GPCV1248 계열 |
| ISP | 하드웨어 ISP 파이프라인 | Gamma, CCM, Sharpen, Denoise, BPC, AE/AWB |
| 센서 | **1MP (1280x720 native) 확정** | UVC 단일 해상도 확인 (Win/Mac), 모델 미확인 |
| 코덱 | GPEncoder (MJPEG), AviPackerV3 (AVI) | |
| 웹캠 출력 | MJPEG 720p → 1080p 업스케일 | UVC 디스크립터: 1280x720 |
| LCD | 160x80 | |
| 플래시 | 1MB SPI (284KB 여유) | |

## 개선 단계

### Phase 0: 해상도 진실 검증 (모든 튜닝의 전제)

**난이도: 낮음 | 영향: 방향 결정 | 촬영 테스트로 확인**

ISP 입력 상한이 720p (GPCV2247F 공식 사양)이므로, 1080P/12M 모드는 업스케일 추정.
이것을 먼저 확정해야 이후 튜닝 기준점이 잡힌다.

| 실험 | 방법 | 판정 기준 |
|------|------|----------|
| 영상 해상도 비교 | 1080P vs 720P 모드로 동일 차트 촬영 | MTF50, 실제 edge detail 차이 |
| 사진 해상도 비교 | 12M/8M/2M/VGA 동일 차트 촬영 | 파일 크기 대비 실제 디테일 |
| Laplacian sharpness | 각 해상도 프레임의 Laplacian variance | 업스케일이면 해상도 높아도 값 동일 |

**결론 (2026-03-29 확정)**: 센서 native = **1280x720 (1MP)**. Windows에서 UVC 해상도 720p만 표시.
1080P/12M/8M/2M = 전부 ISP 스케일러 업스케일. 모든 튜닝은 720p 기준.
→ 상세: `phase0_resolution_truth.md`

### Phase 1: Quick Wins — 바이트 패치 (즉시 적용 가능)

**난이도: 낮음 | 영향: 높음 | SD 업그레이드로 적용**

| # | 수정 | 오프셋 | 변경 | 기대 효과 |
|---|------|--------|------|----------|
| 1-1 | **Brightness 기본값** | 0x08279C, 0x08279E | 0x10→0x80 | 웹캠 밝기 16→128, 어두운 화면 해결 |
| 1-2 | **UVC PU bmControls 확장** | 0x0822AA | 0x01→0x3F | Contrast/Hue/Saturation/Sharpness/Gamma 호스트 제어 활성화 |
| 1-3 | **UVC PU bmControls[1]** | 0x0822AB | 0x00→0x17 | Backlight Comp/Gain/Power Line Freq/WB Auto 활성화 |

**주의**: UVC 컨트롤 비트를 켜도 펌웨어에 GET/SET 핸들러가 없으면 STALL 에러 발생.
→ **1-2는 0x3F 전체가 아닌 단계별 테스트 필요** (0x01→0x03→0x07→0x0F→0x1F→0x3F)

**결론 (2026-03-29 확정)**: UVC 디스크립터 패치만으로는 실질적 화질 개선 불가.
- Brightness 기본값 변경(16→128): AE 자동노출이 장면 맞춰 조절하므로 효과 없음
- bmControls 확장: 호스트 UI에 슬라이더 표시되나, SET_CUR 핸들러 미구현으로 실제 동작 안 함
→ **카메라 독립모드(SD 촬영)의 ISP 직접 튜닝**으로 방향 전환.
→ 상세: `phase1_quick_wins.md`

### Phase 2: JPEG 품질 최적화

**난이도: 중간 | 영향: 높음**

#### 2-1. JPEG 양자화 테이블 분석 및 교체

펌웨어 내 확인된 DQT 테이블 위치:

| 위치 | 종류 | 품질 수준 |
|------|------|----------|
| 0x07C62B | Luminance (Y) | 테스트 이미지용 |
| 0x07C670 | Chrominance (CbCr) | 테스트 이미지용 |
| 0x084438 | Luminance (Y) | 저품질 (값 0x01~0x0F) |
| 0x08447D | Chrominance (CbCr) | 저품질 |

**결론 (2026-03-29 확정)**: Q-테이블 교체 성공 — JPEG 품질 대폭 개선.

수정 펌웨어(`GP1235_phase2_q95.bin`)에서 양자화 테이블을 Q~95 수준으로 교체.
동일 피사체(2M 모드, 1600x1200) 비교 촬영 결과:

| 지표 | 원본 (Q~76) | Phase 2 (Q~97) | 변화 |
|------|------------|----------------|------|
| 파일 크기 | 155.5 KB | 585.8 KB | **3.8배 증가** |
| JPEG Quality 추정 | ~76 | ~97 | **+21** |
| Luma 평균 양자화 | 23.1 | 2.4 | **10배 낮음 (= 고품질)** |
| Laplacian 선명도 | 71 | 101 | **+42% 향상** |
| 8x8 블록 아티팩트 | 1.69 | 1.29 | **-24% 감소** |
| 밝기 평균 | 136.5 | 129.4 | 동등 (각도 차이) |
| 히스토그램 범위 | 31~255 | 30~255 | 동일 |

파일 크기 585KB/프레임 → SD 쓰기 속도(~10MB/s) 이내, 프레임 드롭 없음.

**남은 과제**:
- 2M 모드(1600x1200)는 720p 업스케일이므로 계단 현상 여전 — 해상도 모드 변경 또는 Phase 3에서 샤프닝 조정 필요
- 웹캠 MJPEG 모드의 Q-테이블은 별도 확인 필요

#### 2-2. 웹캠 MJPEG 프레임 크기 조정

UVC 디스크립터의 `dwMaxVideoFrameSize` 조정:
- 오프셋 0x0827B8: 현재 `0x00096000` (614,400 = 720p raw)
- 더 큰 값으로 변경하면 MJPEG 프레임 버퍼 확대 가능

### Phase 3: ISP 기본 파라미터 최적화

**난이도: 중간~높음 | 영향: 중간**

#### 3-1. 설정 블록 (0xC2000) 분석

14개 프로파일 블록(512B×14), 프로파일 0-5 비어있음, 6-13 활성:
```
+0x00: [모드] [비디오해상도] [사진해상도] [플래그]
+0x0F: [Photo Quality] [WB] [노출] [밝기] [색상]
+0x16: [EV] [Sharpness] [Saturation]
+0xA4: [블록 체크섬 CRC32 4바이트]
```

**체크섬 알고리즘 해결 (2026-03-29)**: 표준 CRC32 (polynomial 0xEDB88320), bytes 0x00~0xA3 범위.
8개 활성 프로파일 전부 검증 완료. 패치 도구 `scripts/settings_patch.py` 구현.

**세 가지 체크섬 시스템 (모두 해결됨)**:

| 체크섬 | 알고리즘 | 범위 | 위치 |
|--------|---------|------|------|
| 설정 블록 | CRC32 (0xEDB88320) | 프로파일 bytes 0x00~0xA3 | 각 블록 +0xA4 |
| GPNV 부트로더 | 32비트 워드 XOR | 펌웨어 섹터 | offset 0x08 |
| SD 업그레이드 | 바이트 합산 | 전체 파일 | 파일명에 인코딩 |

**GPNV XOR 주의**: 부팅 화면(0x0AA000)과 버전 문자열(0x079E6C)은 GPNV XOR 범위 **밖**.
이 영역의 변경을 GPNV differential update에 포함하면 체크섬 오류로 **부팅 불가(brick)** 발생.
→ `settings_patch.py`에서 branding 변경은 GPNV word_changes에서 제외 처리됨.

#### 3-2. 메뉴 기본 선택값 변경

| 파라미터 | 오프셋 | 현재(기본) | 매핑 | 상태 |
|----------|--------|-----------|------|------|
| Photo Quality | +0x0F | 0x02 | 1=High, 2=Standard, 3=Economy | ✅ 0x01 적용 (Phase 2 Q-테이블과 중복, 추가 효과 미미) |
| Sharpness | +0x17 | 0x01 | **1=Sharp, 2=Standard/Soft** | ✅ 기본값이 이미 Sharp — 변경 불필요 |
| Saturation | +0x18 | 0x01 | **1=High, 2=Standard/Low** | ✅ 기본값 유지 (0x02는 채도 -39%, 과도한 색빠짐) |
| White Balance | +0x10 | 0x01 Auto | 유지 | — |
| Exposure | +0x11 | 0x01 Auto | 유지 | — |

**Sharpness 경험적 테스트 결과 (v3.0 vs v3.1)**:

| 지표 | 0x17=0x01 (기본) | 0x17=0x02 | 변화 |
|------|-----------------|-----------|------|
| Laplacian 선명도 | 72 | 51 | **-29%** (뚜렷하게 부드러워짐) |
| Edge 강도 | 14.0 | 11.9 | **-15%** |
| 파일 크기 | 620 KB | 585 KB | -6% |

→ 0x17=0x01이 가장 선명한 옵션. 기본값 유지가 최적.

**Saturation 경험적 테스트 결과 (v3.0 vs v3.2)**:

| 지표 | 0x18=0x01 (기본) | 0x18=0x02 | 변화 |
|------|-----------------|-----------|------|
| Saturation 평균 | 119.4 | 73.0 | **-39%** (색빠짐 심각) |
| Chroma noise Cb/Cr | 15.6/17.3 | 13.3/15.3 | -12~15% (소폭 감소) |

→ 크로마 노이즈 감소 효과는 있으나 채도 손실이 과도. 기본값 유지.
→ 크로마 노이즈 근본 해결은 Phase 4 ISP 디노이즈 파라미터 튜닝 필요.

**Phase 3 최종 결론**: 설정 블록 메뉴 기본값은 이미 최적(Sharp/High/Auto).
실질적 화질 개선은 Phase 2 Q-테이블 교체에서 달성. 설정 블록 수정은 추가 효과 미미.
→ 남은 화질 문제(크로마 노이즈, 계단 현상)는 ISP 레지스터 직접 튜닝(Phase 4)으로 전환.

#### 3-3. 펌웨어 식별 (브랜딩)

부팅 화면 "DORORONG" + 버전 문자열로 펌웨어 적용 여부 확인 가능:
- 부팅 화면: 0x0AA000 (160×80 JPEG, max 2285B)
- 버전 문자열: 0x079E6C (USB descriptor, UTF-16LE)
- `scripts/settings_patch.py --brand v3.0` 으로 자동 적용

### Phase 4: 고급 ISP 튜닝 (Ghidra 심층 분석 필요)

**난이도: 높음 | 영향: 높음**

#### 4-1. 감마 커브 커스터마이징

ISP 하드웨어가 RGB 감마 LUT(256엔트리) 지원 확인됨 (GPCV2247F 사양).
- 펌웨어에서 감마 테이블 초기화 코드 찾기
- sRGB 표준 감마(2.2) 또는 커스텀 톤 커브 적용
- 암부 디테일 살리기 (WDR 유사 효과)
- 다이나믹 레인지 개선 기대

#### 4-2. Color Correction Matrix (CCM) 튜닝

3x3 색보정 매트릭스 계수 조정:
- 센서 특성에 맞춘 색재현 개선
- 녹색 색조(tint) 보정
- **피부톤이 자연스럽고 흰색이 깨끗한 방향으로** (정확한 neutral보다 미적 선호 반영)

#### 4-3. 노이즈 리덕션 / 샤프닝 밸런스

저가 카메라의 전형적 문제: 과도한 샤프닝(halo/ringing) 또는 과도한 디노이즈(뭉개짐).
- 인위적 샤프닝 강도 하향 (halo 제거)
- 디노이즈는 저주파 노이즈만 타겟
- 실제 edge는 보존하면서 가짜 윤곽 제거

### Phase 5: 센서 식별 및 AE/Gain 정책 재설계

**난이도: 높음 | 전제: UART 연결 또는 I2C 코드 분석**

#### 5-1. 센서 식별

1. UART 디버그로 부팅 시 I2C 센서 ID 읽기 로그 캡처
2. 또는 Ghidra에서 센서 초기화 I2C 시퀀스 찾기 (주소-값 쌍 테이블)
3. 후보: SP1405, OV2640, GC2035 등
4. 센서 데이터시트로 최적 레지스터 설정 적용

#### 5-2. AE/Gain 정책 수정 (codex 연구 핵심 제안)

저가 카메라 화질을 망치는 가장 흔한 원인 = 과도한 디지털 게인.

목표:
- Analog gain 우선, Digital gain 최소화
- 노출 시간(Integration time) 상한 적절히 설정 (모션 블러 vs 밝기 트레이드오프)
- 야간 모드에서는 밝기보다 노이즈/블러 균형 우선

### Phase 6: 장면별 프리셋 펌웨어

**난이도: 중간 | 영향: 높음 (체감 화질 극대화)**

단일 만능 세팅 대신, 목적별 최적화된 프리셋 세트 제작:

| 프리셋 | AE | Gain | Gamma | Sharpen | Denoise | JPEG Q | WB |
|--------|----|----|-------|---------|---------|--------|-----|
| Photo Best | 느린 셔터 허용 | 최소 | sRGB | 중간 | 강 | 최고 | Auto |
| Video Day | 1/60s 제한 | 낮음 | 밝은톤 | 중간 | 약 | 높음 | Daylight |
| Video Indoor | 1/30s 제한 | 중간 | 표준 | 약 | 중간 | 높음 | Auto |
| Video Night | 1/15s 허용 | 높음 | 암부보정 | 약 | 강 | 중간 | Auto |
| Motion | 1/120s 고정 | 높음 | 표준 | 강 | 약 | 중간 | Auto |

각 프리셋은 설정 블록(0xC2000)의 별도 프로파일로 구현.

## 우선순위 및 일정

```
Phase 0 (해상도 진실)    ████████████  ✅ 완료 — 센서 1280x720 확정
Phase 1 (Quick Wins)     ████████████  ⚠️ 완료 — UVC 패치 효과 없음 → 독립모드 ISP로 전환
Phase 2 (JPEG 품질)      ████████████  ✅ 완료 — Q-테이블 교체 성공 (Q76→Q97, 선명도 +42%)
Phase 3 (ISP 기본값)     ████████████  ✅ 완료 — CRC32 해결, 필드 매핑 완료 (기본값 이미 최적), 브랜딩 시스템
Phase 4 (고급 ISP)       ████          Ghidra 심층 분석
Phase 5 (센서 + AE)      ███           UART/I2C + Gain 정책
Phase 6 (장면별 프리셋)  ████          Phase 3~5 결과 기반
```

## 핵심 연구 과제 5개 (codex 연구 최우선)

1. ~~**1080P / 12M / 8M가 진짜 해상도인지 검증**~~ → Phase 0 ✅ 전부 720p 업스케일 확정
2. ~~**JPEG Q-table 위치와 품질 매핑 찾기**~~ → Phase 2 ✅ Q-테이블 교체 성공
3. ~~**설정 블록(0xC2000) 체크섬 규칙 해독**~~ → Phase 3 ✅ CRC32 확정, 패치 도구 완성
4. **센서 init I2C 시퀀스에서 센서 모델 식별** → Phase 5
5. **AWB/CCM/Gamma 초기화 코드 찾기** → Phase 4

## 측정 기준

각 단계 적용 후 **동일 장면 세트**에서 비교 촬영 (hardware-in-the-loop 방식):

### 측정 지표

| 지표 | 측정 방법 | 목표 |
|------|----------|------|
| 실효 해상도 | MTF50 (slanted-edge) | native 해상도의 이론적 한계에 근접 |
| 밝기 | 평균 픽셀값 | 110~130 |
| 선명도 | Laplacian variance | 현재 대비 2배 이상 (halo 없이) |
| 색정확도 | ColorChecker Delta E | Delta E < 10 (저가 카메라 기준) |
| 색균형 | R/G/B 채널 비율 | 녹색 틴트 제거, 피부톤 자연스러움 |
| 노이즈 | gray patch sigma | 현재 대비 30% 감소 |
| 동적 범위 | 히스토그램 min~max | 암부 뭉개짐/하이라이트 클리핑 최소화 |
| JPEG 아티팩트 | 블로킹/링잉 시각 평가 | 눈에 띄는 블록 노이즈 없음 |
| 프레임레이트 | fps 측정 | 30fps 유지 |
| 파일 크기 | 프레임당 평균 KB | SD 쓰기 속도 이내 |

### 장면 세트 (codex 연구 권장)

1. 실외 주광 (색차트/텍스트)
2. 실내 형광등
3. 실내 텅스텐
4. 저조도
5. 피부톤 (인물)
6. 잔패턴 (모아레 테스트)
7. 역광

## 파일 구조

```
docs/first_plan/
├── README.md              ← 이 문서
├── phase1_quick_wins.md   ← Phase 1 상세 (구현 시 작성)
├── phase2_jpeg_quality.md ← Phase 2 상세
├── phase3_isp_defaults.md ← Phase 3 상세
└── test_results/          ← 각 단계 테스트 결과
```

## 참고 자료

### 내부 분석
- `docs/ongoing/firmware_analysis.md` — 펌웨어 분석 전체 기록
- `docs/ongoing/ghidra_deep_analysis.md` — Ghidra 분석 결과
- `docs/ongoing/sd_upgrade_success.md` — SD 업그레이드 규칙
- `docs/research_isp_capabilities.md` — Generalplus ISP 리서치
- `UVC_Controls_Research.md` — UVC 컨트롤 비트맵 레퍼런스
- `sd_upgrade_tool.py` — 수정 펌웨어 SD 패키징 도구
- `scripts/settings_patch.py` — 설정 블록 패치 + 브랜딩 통합 도구

### 아이디어 소스
- `docs/first_plan/idea/codex/` — 디지털 카메라 IQ 연구 (CVPR/ICCV 논문 기반, 장면별 프리셋 제안, 측정 방법론)
- `docs/first_plan/idea/gemini/` — SP1405 센서 추정, 업스케일 우회, I2C 레지스터 튜닝 제안

### 외부 논문/자료
- Hardware-in-the-Loop ISP Optimization (CVPR 2020) — 측정 기반 반복 튜닝 방법론
- ReconfigISP (ICCV 2021) / DynamicISP (ICCV 2023) — 장면별 ISP 파라미터 분리의 이점
- Camera-Agnostic WB Preferences (ICCVW 2025) — AWB는 정확도보다 미적 선호 반영
- Generalplus GPCV2247F 제품 페이지 — ISP 블록 사양 (Gamma LUT, CCM, Sharpen, Denoise, BPC)
