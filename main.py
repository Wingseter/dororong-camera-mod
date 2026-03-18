"""옴의 법칙(Ohm's Law) 기반 저항 계산 모듈.

전압(V)과 전류(I)를 입력받아 저항(R)을 계산합니다.
공식: R = V / I
"""

import math


def calculate_resistance(voltage: float, current: float) -> float:
    """옴의 법칙을 이용하여 저항을 계산합니다.

    Args:
        voltage: 전압 (V, 볼트)
        current: 전류 (A, 암페어)

    Returns:
        저항 값 (Ω, 옴)

    Raises:
        TypeError: voltage 또는 current가 숫자가 아닌 경우
        ValueError: current가 0에 근접한 경우
    """
    if not isinstance(voltage, (int, float)) or not isinstance(current, (int, float)):
        raise TypeError("전압과 전류는 숫자여야 합니다.")
    if math.isclose(current, 0, abs_tol=1e-12):
        raise ValueError("전류는 0이 될 수 없습니다.")
    return voltage / current


def main():
    """전압과 전류로부터 저항을 계산하여 출력합니다."""
    voltage = 5.0  # V
    current = 0.02  # A (20mA)
    resistance = calculate_resistance(voltage, current)
    print(f"전압: {voltage}V, 전류: {current}A")
    print(f"저항: {resistance}Ω")


if __name__ == "__main__":
    main()
