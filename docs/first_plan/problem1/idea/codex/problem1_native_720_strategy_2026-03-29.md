# Problem 1: Native 720p Still Path Research

> 작성일: 2026-03-29
> 대상: `docs/first_plan/problem1/README.md`
> 목적: `1600x1200` 업스케일 사진 경로를 `1280x720 native`에 최대한 가깝게 바꾸는 실험 순서를 재정리

## TL;DR

가장 중요한 새 발견은 이것이다.

1. `mode 3`은 `1280x720`이 아니라 `1280x960`이다.
2. 따라서 README의 "mode 3 강제 선택" 아이디어는 native 720 해결책이 아니다.
3. 첫 brick의 가장 유력한 원인은 `0x1C764 / 0x1C870` 같은 width-only 경로까지 한 번에 건드려 런타임 파이프라인을 깨뜨린 것이다.
4. 다음 실험은 `0x1FDD4 / 0x1FDD8`의 JPEG 입력 width/height 쌍만 최소 패치하고, width-only 경로는 그대로 두는 쪽이 더 안전하다.

## 1. 바이너리 재확인 결과

### 1-1. 사진 해상도 스위치 테이블의 실제 해석

`analysis/GP1235_firmware.bin`에서 `0x1FDB0~0x1FDF0` 구간을 다시 디코드하면 다음과 같다.

| 오프셋 | 명령 | 값 | 의미 |
|---|---|---:|---|
| `0x1FDB4` | `MOV R4, #0xFC0` | 4032 | 12M width |
| `0x1FDB8` | `MOV R5, #0xBD0` | 3024 | 12M height |
| `0x1FDC4` | `MOV R4, #0xCC0` | 3264 | 8M width |
| `0x1FDC8` | `MOV R5, #0x990` | 2448 | 8M height |
| `0x1FDD4` | `MOV R4, #0x640` | 1600 | 2M width |
| `0x1FDD8` | `MOV R5, #0x4B0` | 1200 | 2M height |
| `0x1FDEC` | `MOV R4, #0x500` | 1280 | 1M width |
| `0x1FDF0` | `MOV R5, #0x3C0` | 960 | 1M height |
| `0x1DE4/0x1DE8` | `MOVNE R4/R5` | 640x480 | VGA fallback |

즉 사진 모드 테이블은 사실상 다음과 같다.

| mode | 해상도 | 메뉴 추정 |
|---|---|---|
| 0 | `4032x3024` | 12M |
| 1 | `3264x2448` | 8M |
| 2 | `1600x1200` | 2M |
| 3 | `1280x960` | 1M |
| fallback | `640x480` | VGA |

핵심은 `mode 3 = 1280x960`이라는 점이다. README의 `mode 3에 이미 native 1280이 존재`라는 문장은 width만 맞고, height는 다르다.

### 1-2. width-only 테이블도 동일한 4:3 사진 계층을 따른다

`0x1C740`대와 `0x1C850`대에도 같은 해상도 계층이 반복된다.

| 오프셋 | 역할 추정 | mode 2 | mode 3 | fallback |
|---|---|---:|---:|---:|
| `0x1C764` | width-only helper A | 1600 | 1280 | 640 |
| `0x1C870` | width-only helper B | 1600 | 1280 | 640 |

이 두 경로는 분기 후 공통 함수 `0x019260`을 호출한다. 따라서 단순 메타데이터가 아니라 stride, 버퍼 폭, 또는 하위 할당 경로일 가능성이 높다. 이 둘을 초기에 같이 줄이는 것은 위험하다.

### 1-3. 공통 해상도 인덱스 헬퍼가 존재한다

`0x1C744`, `0x1C850`, `0x1FDAC`는 모두 같은 함수 `0x02EEF8`을 먼저 호출한 뒤 분기 테이블을 탄다.

이 말은 사진 해상도 선택이 한 곳에서 공통으로 들어오고, 이후

- width-only 경로
- 또 다른 width-only 경로
- JPEG 입력 width/height 경로

로 흩어진다는 뜻이다.

## 2. 이 발견이 뜻하는 것

### 2-1. README의 접근 B는 native 720 해결책이 아니다

`mode 2 -> mode 3`으로 강제해도 결과는 `1280x960` 4:3 still 경로다. 즉:

- native `1280x720` 16:9로 바로 떨어지지 않는다.
- 오히려 센서 native와 aspect ratio가 다르므로 또 다른 스케일 또는 crop 경로일 가능성이 높다.

따라서 `mode 3 강제 선택`은 "2M보다 덜 나쁜 1M still" 실험은 될 수 있어도, 목표인 `native 720p still`의 정답은 아니다.

### 2-2. 현재 사진 모드는 4:3 still 파이프라인일 가능성이 높다

로컬 문서상 이미 확정된 사실:

- 센서 native는 `1280x720`
- UVC/video path는 `1280x720`
- UVC `dwMaxVideoFrameSize`는 `0x00096000` = `614,400` = `1280x720x1.5`

반면 사진 테이블은 `4032x3024 / 3264x2448 / 1600x1200 / 1280x960 / 640x480`의 전형적인 4:3 still SKU 표다.

즉 문제의 본질은 단순히 "1600을 1280으로 바꾸자"가 아니라:

`16:9 native video/UVC path`와 `4:3 still path`가 분리되어 있고, 현재 사진 촬영은 후자만 탄다.

## 3. 첫 brick의 가장 그럴듯한 원인

체크섬보다 런타임 파이프라인 불일치 가능성이 더 크다.

이유:

1. SD 업그레이드 경로는 별도 문서에서 이미 성공이 확인되었다.
2. `settings_patch.py`는 raw patch도 GPNV XOR 차분 업데이트에 포함한다.
3. 첫 시도는 아래 네 곳을 한 번에 바꿨다.

```text
0x1FDD4  1600 -> 1280
0x1FDD8  1200 -> 720
0x1C764  1600 -> 1280
0x1C870  1600 -> 1280
```

이 구성은 JPEG 입력 크기뿐 아니라 width-only 보조 경로 둘까지 동시에 축소한다. 만약 `0x1C764 / 0x1C870`가

- row stride
- DMA pitch
- scratch buffer width
- scaler output width

중 하나라도 잡고 있다면, 1600 기준으로 설계된 하위 경로와 충돌할 수 있다.

반대로 `0x1FDD4 / 0x1FDD8`만 바꾸면 "버퍼는 크게 남겨두고, 최종 JPEG 입력만 줄이는" 형태가 되므로 실패 반경이 더 작다.

## 4. 권장 전략

### 1순위: JPEG 입력 쌍만 최소 패치

목표는 원인 분리다. 다음 실험은 아래 두 곳만 바꾸는 것이 맞다.

```text
0x1FDD4: 0x03A04E64 -> 0x03A04E50   ; 1600 -> 1280
0x1FDD8: 0x03A05E4B -> 0x03A05E2D   ; 1200 -> 720
```

주의할 점:

- `1280` 인코딩은 기존 `mode 3`와 같은 `0x03A04E50`을 쓰는 편이 낫다.
- 기존 시도처럼 `0x03A04C05`도 값은 같지만, 펌웨어가 이미 쓰는 형태를 재사용하는 편이 더 보수적이다.
- `0x1C764`, `0x1C870`는 첫 실험에서 건드리지 않는다.

이 실험의 의미:

- 부팅 성공 + JPEG가 `1280x720`이면 바로 목표에 근접한다.
- 부팅 성공 + 화면 왜곡이면 stride/helper 문제를 추가 추적하면 된다.
- 여전히 brick이면 그때는 checksum/UART/boot path를 다시 본다.

### 2순위: width-only 경로는 하나씩 추적 후 패치

최소 패치에서 왜곡이나 실패가 생기면 다음 대상은 `0x1C764`, `0x1C870`다. 다만 둘을 동시에 바꾸지 말고:

1. 어떤 호출자가 실제 버퍼 폭을 잡는지 확인
2. `0x019260`의 파라미터 의미 확인
3. 한 곳씩 분리 패치

순서로 가는 편이 맞다.

### 3순위: still path를 버리고 720 video path를 재사용

장기적으로는 이 방향이 더 깔끔할 수 있다.

근거:

- still 테이블에는 `720`이 없다.
- video/UVC path에는 `720`이 이미 존재한다.

즉 "사진 한 장 저장"을 still 4:3 파이프라인에서 해결하려 하지 말고,

- video snapshot
- GPEncoder single-frame path
- 720 buffer dump 후 JPEG 래핑

같은 우회가 더 본질적일 수 있다.

이 방향은 구현 난도가 높지만, native 720을 가장 정직하게 얻을 가능성이 크다.

## 5. 권장 실험 순서

### 실험 A: 최소 패치

패치:

```text
0x1FDD4 -> 0x03A04E50
0x1FDD8 -> 0x03A05E2D
```

배포:

- SD 업그레이드 경로 사용
- `sd_upgrade_tool.py` 또는 기존 파일명 규칙 사용

관찰:

1. 부팅 여부
2. 촬영 가능 여부
3. JPEG SOF 해상도
4. 화면 왜곡 여부
5. 계단 현상 감소 여부

### 실험 B: 최소 패치 성공, 그러나 왜곡 발생

해야 할 것:

- `0x019260` 호출부 분석
- `0x1C764` 또는 `0x1C870` 중 어느 쪽이 stride/alloc인지 구분
- width-only 패치를 한 곳씩 추가

### 실험 C: 최소 패치에서도 부팅 실패

그때 확인할 것:

1. GPNV XOR 실제 반영값
2. UART에서 boot log 확인
3. patch 대상 word 정렬/엔디언 문제 재검증
4. `0x1FDD4/0x1FDD8`가 단순 상수가 아니라 다른 계산과 결합되는지 확인

## 6. 바로 쓸 수 있는 패치 명령 예시

```bash
python scripts/settings_patch.py analysis/GP1235_phase3.bin ^
  --raw-patch 0x1FDD4=0x03A04E50 ^
  --raw-patch 0x1FDD8=0x03A05E2D ^
  -o analysis/GP1235_problem1_minimal_720.bin
```

그 다음 SD 업그레이드용 파일명은 기존 성공 규칙을 그대로 사용한다.

## 7. 결론

현재 문제는 "이미 있는 720 모드를 찾기"보다 "4:3 still 경로에서 16:9 native path로 빠져나오기"에 가깝다.

가장 중요한 수정 포인트는 두 가지다.

1. `mode 3 = 1280x960`이라는 사실을 전제로 다시 판단할 것
2. 다음 실험은 `0x1FDD4/0x1FDD8`만 건드리는 최소 패치로 원인을 분리할 것

즉 다음 한 번의 실험은 "더 많이 고치기"가 아니라 "덜 건드리고 더 많이 알아내기"가 맞다.

## 참고한 로컬 근거

- `docs/first_plan/problem1/README.md`
- `docs/first_plan/README.md`
- `docs/first_plan/phase0_resolution_truth.md`
- `docs/ongoing/sd_upgrade_success.md`
- `docs/ongoing/sd_upgrade_test.md`
- `docs/ongoing/ghidra_deep_analysis.md`
- `scripts/settings_patch.py`
- `analysis/GP1235_firmware.bin`
