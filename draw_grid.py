import sys
try:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open('KakaoTalk_Photo_2026-03-21-23-54-06.jpeg')
    draw = ImageDraw.Draw(img)
    w, h = img.size
    rows, cols = 10, 10
    for i in range(1, cols):
        x = int(i * w / cols)
        draw.line([(x, 0), (x, h)], fill='red', width=5)
    for i in range(1, rows):
        y = int(i * h / rows)
        draw.line([(0, y), (w, y)], fill='red', width=5)
    for r in range(rows):
        for c in range(cols):
            x = int((c + 0.5) * w / cols) - 50
            y = int((r + 0.5) * h / rows) - 50
            # Try to draw text without custom font
            draw.text((x, y), f"{c},{r}", fill='yellow', font_size=100) # Only works in newer Pillow, let's use default if needed
    img.save('grid_img.jpeg')
    print("Grid image saved successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
