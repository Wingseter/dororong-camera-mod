# 펌웨어 덤프 진행 기록

> 일시: 2026-03-28

## 장비

- CH341A 프로그래머 (3.3V 개조 완료, 핀 28 리프트)
- SOP8 클립
- ANENG A830L 멀티미터

## 진행 과정

1. CH341A 3.3V 개조 (핀 28 리프트 → AMS1117 3.3V 출력 연결)
2. 멀티미터로 VCC 전압 확인: **3.17V** (PY25D80HB 스펙 2.3~3.6V 범위 내)
3. 배터리 빨간선(B+) 인두로 분리
4. SOP8 클립 → PY25D80HB 칩에 연결
5. 클립 방향 수정 후 칩 ID 읽기 성공: `id1=0x85, id2=0x2014`
6. flashrom `--force` 옵션으로 1MB 전체 덤프 2회 수행
7. MD5 일치 확인 → 덤프 성공

## 결과

| 항목 | 값 |
|------|-----|
| 파일 | `firmware_backup_1.bin` / `firmware_backup_2.bin` |
| 크기 | 1,048,576 bytes (1MB) |
| MD5 | `72997afac0265ebedb77bf4cf912c7ca` |
| 칩 ID | Manufacturer=0x85 (PUYA), Type=0x20, Capacity=0x14 (8Mbit) |
| 헤더 | `GPNV` (Generalplus 펌웨어 확인) |
| 데이터 분포 | 46.3% 유효 / 28.2% 0x00 / 25.5% 0xFF |

## 주의사항

- flashrom이 칩 ID 자동 매칭 실패 → `--force -c P25D80H` 필요
- 쓰기 시에도 동일 옵션 필요할 것
- `firmware_backup_1.bin`은 원본 보존용 — 절대 수정 금지
