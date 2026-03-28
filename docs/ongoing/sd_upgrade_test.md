# SD 카드 업그레이드 테스트 결과

> 일시: 2026-03-29
> 테스트: 원본 펌웨어를 JH_5307.bin으로 SD에 복사 후 부팅

## 테스트 결과

**실패** — `"Program error please check file"` 표시 후 전원 꺼짐

## 카메라 반응 분석

1. 파일명 `JH_5307.bin` 인식 ✅
2. 업그레이드 루틴 진입 ✅
3. 파일 검증 **실패** ❌ → "Program error"
4. 자동 전원 종료

## 실패 원인: 체크섬 불일치

### 업그레이드 함수 코드 분석 (FUN_00041678)

디스어셈블 결과에서 확인된 체크섬 검증 흐름:

```
1. 파일을 0x40000(256KB) 단위로 읽기
2. 각 바이트를 누적 합산 (전역변수 0x0007DC14에 저장)
3. 동시에 처음 3바이트를 "GPN" 매직과 비교
4. 모든 읽기 완료 후:
   - 계산된 합산값 (전역변수에서 로드)
   - 기대 체크섬값 (FUN_00041508 반환값)
   - 두 값을 CMP 비교
5. 불일치 → R11 = 1 (에러 플래그)
6. R11 != 0 → "Program error" + "Please check file" 표시
```

### FUN_00041508: 체크섬 기대값 추출

이 함수는 **hex 문자열 파서** (strtoul 유사):
- 입력: findfile 결과 구조체(0x0007DC18) + offset 35에서 복사한 8바이트
- 파싱: '0'-'9', 'a'-'f', 'A'-'F' 문자를 숫자로 변환
- 출력: 32비트 정수 (체크섬 기대값)

기대값 = GPNV 헤더 offset 0x08의 값 = **0x0BD04FA2**

### 계산된 값 vs 기대값

| 항목 | 값 |
|------|------|
| 기대 체크섬 (GPNV 0x08) | 0x0BD04FA2 |
| 전체 파일 바이트 합 | 0x07704B0D |
| 차이 | 0x04600495 |

**결론: GPNV 체크섬은 단순 바이트 합산이 아님**

### 시도한 알고리즘 (전부 불일치)

| 알고리즘 | 범위 | 결과 |
|----------|------|------|
| 바이트 합 | 전체 파일 | 0x07704B0D |
| 바이트 합 | 체크섬 필드 제외 | 0x07704941 |
| 16비트 워드 합 | 전체 | 0xDF7E2945 |
| 32비트 워드 합 | 전체 | 0xEEBFC122 |
| CRC-32 (standard) | 전체 | 0xCACC024E |
| CRC-32C (Castagnoli) | 전체 | 불일치 |
| Fletcher-32 | 전체 | 0x053DAD54 |
| XOR (32bit) | 전체 | 0x3205C83E |
| 바이트 합 | 0x200~0x3000 | 0x000EB952 |
| 바이트 합 | 0x12C00~0xB4000 | 0x03AD0D5E |
| 바이트 합 | 0x100 경계 모든 조합 | 일치 없음 |

## FUN_00041de4: 빌드 문자열 비교

### 구조체 분석

findfile 결과 구조체 (0x0007DC18, 119바이트):
- offset +0x16 (22): 빌드 문자열 비교에 사용
- offset +0x23 (35): 체크섬 hex 문자열에 사용

```c
// 빌드 비교 (FUN_00041de4)
memcmp(struct + 0x16, "2025004291200", 12);
// 다르면 → 업그레이드 진행, 같으면 → 스킵

// 체크섬 추출 (FUN_00041678 내)
memcpy(buf, struct + 35, 8);  // 8바이트 hex 문자열
expected = hex_parse(buf);     // → 0x0BD04FA2
```

### 빌드 문자열 "2025004291200"

- 위치: 0x041E84 (펌웨어 코드에 하드코딩)
- 길이: 13바이트 (12바이트만 비교)
- 해석: 정확한 포맷 불명 (날짜 인코딩 추정)
- 관련: `"5307 20260129"` (0x03C43C, 빌드 정보)

## ARM 디스어셈블 주요 발견

### 이전 분석 오류 수정

| 항목 | 이전 분석 | 실제 |
|------|----------|------|
| LDRB R6, [R11, #4] | 고정 오프셋 +4 | **LDRB R6, [R11, R4]** (레지스터 인덱스) |
| CMN R0, #2 | R0 == 2 확인 | R0 + 2 == 0 → **R0 == -2** 확인 |
| 체크섬 변수 | 스택 로컬 | **전역 변수** (0x0007DC14) |

### 매직 검증 확인

매직 참조 포인터 = 0x000670EE (RAM)
→ Flash 0x079CEE에 `"GPNV"` 데이터 존재 ✅
처음 3바이트 `"GPN"` 비교

## 해결 방안

### 1순위: CH341A 직접 쓰기

- SD 업그레이드 체크섬을 우회할 수 있는 유일한 확실한 방법
- 부트로더(0x000~0x3000)는 건드리지 않고 메인 코드만 수정
- 부트로더가 메인 코드 체크섬을 별도로 검증하는지는 미확인
  - `"GPNVBtLdr Recover"` 기능이 있으므로 실패 시 복구 가능성
- 실패해도 `firmware_backup_1.bin`으로 원본 복원 가능

### 2순위: UART 디버그

- CP2102를 SoC 핀 1 근처 빈 패드에 연결 (3.3V!)
- `"GPNVNV checksum:0x%08x"` 부트 로그에서 체크섬 값 확인
- 부팅 과정의 체크섬 계산 과정 관찰 가능

### 3순위: 부트로더 심층 역분석 → 완료!

## 부트로더 체크섬 역분석 결과

### 알고리즘: 32비트 워드 XOR

부트로더 FUN_001710 (Thumb 코드) 디컴파일:

```c
// flash 0x001710 (runtime 0x1F9510)
uint32_t checksum(uint32_t* data, uint32_t word_count, uint32_t init) {
    uint32_t result = init;  // init = 0
    for (int i = 0; i < word_count; i++) {
        result ^= data[i];   // EOR R0, R3 ← XOR!
    }
    return result;
}
```

핵심 명령어:
```
0x001710: PUSH {R4}
0x001712: MOV R4, R0        ; R4 = 데이터 포인터
0x001714: MOV R0, R2        ; R0 = 초기값 (0)
0x001716: MOV R2, #0        ; 인덱스 = 0
0x001718: B loop_check
loop:
0x00171A: LSL R3, R2, #2    ; R3 = index * 4
0x00171C: LDR R3, [R4, R3]  ; R3 = data[index]
0x00171E: EOR R0, R3         ; result ^= data[index]  ★★★
0x001720: R2++               ; index++
loop_check:
0x001722: CMP R2, R1         ; index < word_count?
0x001724: BCC loop           ; continue
```

### 부트로더 체크섬 검증 흐름 (0x15C0~0x15DE)

```
1. 구조체에서 섹터 수 읽기 (offset 20)
2. 마지막 섹터의 첫 4바이트 = 기대 체크섬 (R6에 저장)
3. XOR 범위 = 0 ~ (섹터수-1)*512 바이트
4. checksum(data_ptr, word_count, 0) 호출
5. printf("GPNVNV checksum:0x%08x", 계산값)
6. printf("Btldr checksum:0x%08x", 기대값)
7. CMP 계산값, 기대값
8. 불일치 → printf("BtLdr NV-Source CheckSum error, Recover it back")
9. 복구 시도 (GPNVBtLdr Recover)
```

### 두 가지 체크섬 시스템

| 항목 | 부트로더 검증 | SD 업그레이드 검증 |
|------|-------------|------------------|
| 알고리즘 | **32비트 워드 XOR** | **바이트 합산 (ADD)** |
| 코드 위치 | FUN_001710 (Thumb) | FUN_00041678 (ARM) |
| 핵심 명령 | `EOR R0, R3` | `ADD R2, R1, R2` |
| 기대값 출처 | 마지막 섹터 첫 워드 | 전역 구조체 hex 파싱 |
| 실패 시 | 복구 시도 후 부팅 | "Program error" 종료 |

### CH341A 수정 시 XOR 체크섬 보정

XOR의 특성을 이용해 차분 계산 가능:

```
1. old_word = 수정 전 워드 (4바이트 정렬)
2. new_word = 수정 후 워드
3. diff = old_word ^ new_word
4. new_checksum = old_checksum ^ diff
5. GPNV offset 0x08에 new_checksum 기록
```

Brightness 수정 예시:
```
old_word @ 0x08279C: 0x00100010 (밝기 16, 16)
new_word:            0x00800080 (밝기 128, 128)
XOR diff:            0x00900090
old_checksum:        0x0BD04FA2
new_checksum:        0x0B404F32
```

### 부트로더 복구 메커니즘

체크섬 실패 시 `"GPNVBtLdr Recover well done"` 메시지가 존재하므로 자동 복구 가능성 있음. CH341A로 수정 시 체크섬이 틀려도 복구 후 부팅될 수 있음.
