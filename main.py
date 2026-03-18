def calculate_resistance(voltage, current):
    """옴의 법칙을 이용하여 저항을 계산합니다."""
    if current == 0:
        raise ValueError("전류는 0이 될 수 없습니다.")
    return voltage / current


def main():
    voltage = 5.0  # V
    current = 0.02  # A (20mA)
    resistance = calculate_resistance(voltage, current)
    print(f"전압: {voltage}V, 전류: {current}A")
    print(f"저항: {resistance}Ω")


if __name__ == "__main__":
    main()
