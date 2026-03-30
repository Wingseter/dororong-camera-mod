#!/bin/bash
# USB 장치 변화 실시간 모니터링
# 버튼 조합 ISP 모드 실험 시 사용
# 사용법: ./scripts/usb_monitor.sh

echo "=== USB Device Monitor ==="
echo "새 USB 장치가 연결/변경되면 표시됩니다."
echo "Ctrl+C로 종료"
echo ""

# 초기 상태 저장
PREV=$(ioreg -p IOUSB -l 2>/dev/null | grep -E "idVendor|idProduct|USB Product Name" | sort)

while true; do
    CURR=$(ioreg -p IOUSB -l 2>/dev/null | grep -E "idVendor|idProduct|USB Product Name" | sort)

    if [ "$PREV" != "$CURR" ]; then
        echo ""
        echo ">>> $(date '+%H:%M:%S') USB 변화 감지! <<<"
        echo ""
        # 새로 추가된 라인
        diff <(echo "$PREV") <(echo "$CURR") | grep "^>" | while read line; do
            echo "  + $line"
        done
        # 제거된 라인
        diff <(echo "$PREV") <(echo "$CURR") | grep "^<" | while read line; do
            echo "  - $line"
        done
        echo ""
        echo "--- 현재 전체 USB 장치 ---"
        ioreg -p IOUSB -l 2>/dev/null | grep -E "idVendor|idProduct|USB Product Name" | sed 's/^/  /'
        echo "---"
        PREV="$CURR"
    fi

    sleep 0.5
done
