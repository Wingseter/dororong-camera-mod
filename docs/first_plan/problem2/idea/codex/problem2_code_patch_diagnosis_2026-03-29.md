# Problem 2: Code-Area Patch Brick Diagnosis

> 작성일: 2026-03-29
> 대상: `docs/first_plan/problem2/README.md`
> 목적: "0x01xxxx 패치 = 무조건 brick" 가설을 검증 가능한 형태로 다시 정리

## TL;DR

현재 증거만으로는 아직 `코드 영역 자체가 보호된다`고 결론 내리기 어렵다.

핵심 이유는 세 가지다.

1. 실패한 패치는 아직 2건뿐이고, 둘 다 같은 해상도 패치 계열이다.
2. 그 해상도 패치 자체가 런타임 의미상 매우 위험했다.
3. `settings_patch.py`는 GPNV XOR을 "검증"하지 않고, 단지 미확정 가정으로 차분 업데이트만 한다.

따라서 Problem 2의 본질은 지금 시점에서

- `코드 영역 보호` 문제일 수도 있고
- `체크섬 경계 오판` 문제일 수도 있고
- 그냥 `720 still 패치 자체가 잘못된` 문제일 수도 있다.

이 셋을 먼저 분리해야 한다.

## 1. README에서 바로 수정해야 하는 전제

### 1-1. `0x01xxxx 영역 패치 = 항상 brick`은 아직 성급한 결론이다

현재 실패 이력:

| 시도 | 패치 | 성격 |
|---|---|---|
| 1차 | `0x1FDD4`, `0x1FDD8`, `0x1C764`, `0x1C870` | 해상도 + width-only helper 동시 변경 |
| 2차 | `0x1FDD4`, `0x1FDD8` | 해상도만 변경 |

둘 다 같은 기능군이다. 즉 지금까지 증명된 것은

`사진 해상도 경로를 1600x1200 -> 1280x720로 바꾸는 패치가 brick를 일으켰다`

뿐이지,

`코드 영역은 어떤 패치도 허용하지 않는다`

까지는 아니다.

### 1-2. Problem 1 분석 결과상, 실패 패치 자체가 위험했다

이미 `problem1` 분석에서 확인한 것:

- `mode 3`은 `1280x720`이 아니라 `1280x960`
- `0x1C764`, `0x1C870`는 width-only helper라서 stride/buffer 관련일 가능성이 높음
- `0x1FDD4`, `0x1FDD8`의 `1280x720` 주입은 4:3 still 경로에 16:9 크기를 억지로 넣는 패치임

즉 이 brick는 "코드 영역이라서"가 아니라 그냥

- 버퍼 폭/height/overlay/stride 불일치
- still pipeline에서 지원하지 않는 aspect ratio
- 또는 예상 밖 하위 함수 파라미터 붕괴

때문일 가능성도 충분히 높다.

### 1-3. `0x0B4000` 실험은 코드 영역 검증으로 부적절하다

README의 실험 1 초안은 `0x0B4000~0x0C2000` 패딩 영역 1바이트 변경을 제안한다.

이건 핵심 실험으로는 부적절하다.

이유:

- 해당 영역은 `docs/ongoing/firmware_analysis.md` 기준 main firmware 밖의 패딩 영역이다.
- 즉 여기서 부팅 성공해도 `코드 영역 패치 가능`은 증명되지 않는다.
- 반대로 실패해도 패딩/헤더/경계 처리 문제일 수 있어 해석이 나빠진다.

이 실험은 분리 실험으로 정보량이 낮다.

## 2. 가장 중요한 도구상의 문제

### 2-1. `settings_patch.py`는 GPNV XOR을 실제 검증하지 않는다

스크립트의 핵심 동작:

- `calc_gpnv_xor(data)`는 "파일 전체 32-bit XOR"을 가정
- `update_gpnv_xor_differential(...)`도 그 가정 위에서 old/new word의 XOR diff만 반영
- `verify_all_checksums()`는 GPNV를 다시 계산해 stored 값과 비교하지 않고, 그냥 저장값만 출력

즉 현재 도구는 다음을 보장하지 않는다.

- `offset 0x08`이 실제 bootloader 기대값과 일치하는지
- XOR 범위가 어디까지인지
- 특정 영역이 checksum 범위 밖인지

실제로 원본 펌웨어에 대해 `offset 0x08 = 0x0BD04FA2`와 파일 전체 XOR은 일치하지 않는다. 따라서 스크립트의 "full-image XOR" 가정은 아직 검증되지 않았다.

결론:

`코드 영역 패치 후 GPNV XOR도 업데이트했다`는 사실은,
`그래서 체크섬이 맞다`는 뜻이 아니다.

## 3. 현재 가장 그럴듯한 가설 순위

### 가설 A: 해상도 패치 자체가 런타임에서 잘못되었다

가장 가능성이 높다.

근거:

- 실패 2건이 모두 같은 still-resolution patch
- 첫 시도는 width-only helper까지 같이 수정
- 둘째 시도도 여전히 4:3 still path에 16:9 height를 주입
- Problem 1에서 이미 `mode 3 = 1280x960`로 확인되어 사진 파이프라인 자체가 4:3 중심임

### 가설 B: 코드/rodata가 포함된 main firmware 영역은 bootloader checksum 경계 안이다

충분히 가능하다.

근거:

- bootloader에는 별도 checksum/recover 메시지가 있음
- `settings_patch.py`의 XOR 가정은 미검증
- 코드 세그먼트 패치가 실패한 이유가 region 때문일 수도 있음

다만 아직 `해상도 패치` 외의 무해한 code-segment patch 실험이 없다.

### 가설 C: SD 업그레이드 루틴이 main firmware 일부를 별도 취급한다

가능하지만 A/B보다 후순위다.

이건 CH341A 직접 쓰기와 비교해야만 분명해진다.

## 4. 더 좋은 실험 설계

문제는 "코드 영역을 바꾸면 무조건 죽나?"이지, "720 still 패치가 안전한가?"가 아니다.

따라서 첫 실험은 반드시 **의미적으로 무해한 패치**여야 한다.

### 실험 1: main firmware 안의 비실행 문자열 패치

가장 추천하는 첫 실험이다.

후보:

| 오프셋 | 내용 | 이유 |
|---|---|---|
| `0x041A18` | `"Upgrading firmware..."` | 정상 부팅 시 사용되지 않는 업그레이드 UI 문자열 |
| `0x041DAC` | `"Upgrade fail"` | 정상 부팅 시 사용되지 않는 오류 문자열 |
| `0x041E84` | `"2025004291200"` | 업그레이드 비교용 하드코딩 빌드 문자열, 정상 부팅에는 비핵심 |

이 셋은 모두 `0x012000~0x0B4000` main firmware 안에 있지만,
정상 부팅 경로에서 실행 의미가 거의 없다.

예시:

- `"Upgrading firmware..."`의 한 글자만 변경
- `"Upgrade fail"`의 한 글자만 변경

해석:

- 이 패치가 SD 업그레이드 후 정상 부팅되면
  - `main firmware 영역 자체는 패치 가능`
  - 기존 brick는 해상도 패치 의미 문제일 가능성이 커짐
- 이 패치도 brick면
  - checksum/bootloader/main-region 보호 가설이 강해짐

이 실험이 `0x0B4000` 패딩 실험보다 훨씬 낫다.

### 실험 2: 같은 rodata 패치를 CH341A로 직접 쓰기

실험 1이 brick일 경우 바로 이어서 해야 한다.

해석:

- `SD`는 brick, `CH341A`는 부팅 성공
  - SD 업그레이드 경로 또는 기록 후 메타 처리 문제가 원인
- `SD`도 brick, `CH341A`도 brick
  - bootloader 또는 정상 부팅 시 main firmware 무결성 검증 가능성 상승

즉 이 비교 한 번으로

- 업그레이드 루틴 문제
- 부팅시 검증 문제

를 크게 분리할 수 있다.

### 실험 3: 그 다음에야 실행 코드 1-instruction 패치

rodata 패치가 통과한 뒤에만 권장한다.

좋은 후보 조건:

- 정상 부팅 중 실행되지 않는 함수
- 업그레이드 UI/오류 처리 함수 내부
- 분기/리터럴 로드 하나만 바꿔도 의미가 제한적인 곳

나쁜 후보:

- 해상도/버퍼/센서 경로
- 벡터 테이블 근처
- 초기화 루틴

## 5. 추천 실험 매트릭스

| 실험 | 패치 위치 | 성격 | 배포 경로 | 해석 가치 |
|---|---|---|---|---|
| A | `0x041A18` 또는 `0x041DAC` | rodata, 무해 | SD | 최고 |
| B | A와 동일 | rodata, 무해 | CH341A | 최고 |
| C | 업그레이드 전용 함수 내부 instruction 1개 | code, 저위험 | SD | 중간 |
| D | `0x1FDD4/0x1FDD8` | code, 고위험 | SD | 낮음 |

현재 상태에서 D부터 반복하는 것은 정보량이 낮다.

## 6. 가장 합리적인 다음 순서

1. `problem2`의 첫 제어 실험은 `0x041A18` 또는 `0x041DAC` 문자열 1바이트 변경으로 잡는다.
2. 이 실험이 SD에서 성공하면, Problem 2는 사실상 "코드 세그먼트 전체 보호" 문제가 아니다.
3. 이 실험이 SD에서 실패하면, 같은 패치를 CH341A로 바로 비교한다.
4. 그 뒤에야 GPNV 범위 brute-force 또는 bootloader 디스어셈블을 더 깊게 들어간다.
5. `0x1FDD4/0x1FDD8` 같은 해상도 패치는 Problem 2의 진단 실험으로 쓰지 않는다.

## 7. README에 반영하면 좋은 수정안

### 수정 1

현재 문장:

`패턴: 0x01xxxx 영역 패치 = 항상 brick`

추천 수정:

`현재까지는 still 해상도 관련 code patch 2건이 brick를 일으켰다. 아직 code segment 전체 보호인지, 패치 의미 문제인지는 분리되지 않았다.`

### 수정 2

현재 실험:

`0x0B4000 패딩 영역 1바이트 변경`

추천 수정:

`main firmware 내부의 비실행 문자열(예: 0x041A18, 0x041DAC) 1바이트 변경`

### 수정 3

가설 우선순위:

기존 README는 `코드 영역 별도 검증`을 가장 유력으로 두고 있는데,
현재 증거만으로는

1. 해상도 패치 의미 문제
2. 미검증 GPNV/XOR 가정 문제
3. code/main-firmware integrity 검증

순으로 보는 편이 더 방어적이다.

## 8. 결론

Problem 2는 아직 `코드 영역 보호 문제`로 확정된 상태가 아니다.

오히려 지금까지의 증거로 보면,

- 실험 대상이 너무 위험했고
- 체크섬 도구 가정도 검증되지 않았고
- 제어 실험이 main firmware 내부에서 아직 한 번도 수행되지 않았다.

따라서 가장 좋은 해결 아이디어는

`코드 세그먼트 안의 무해한 rodata 패치 -> SD/CH341A 비교 -> 그 다음에만 실행 코드 패치`

순으로 진단 순서를 재설계하는 것이다.

이 순서를 따르면 Problem 2는 `보호 메커니즘 문제`인지 `해상도 패치 문제`인지 빠르게 분리할 수 있다.

## 참고한 로컬 근거

- `docs/first_plan/problem2/README.md`
- `docs/first_plan/problem1/idea/codex/problem1_native_720_strategy_2026-03-29.md`
- `docs/ongoing/sd_upgrade_test.md`
- `docs/ongoing/sd_upgrade_success.md`
- `docs/ongoing/firmware_analysis.md`
- `docs/ongoing/additional_findings.md`
- `scripts/settings_patch.py`
- `analysis/GP1235_firmware.bin`
