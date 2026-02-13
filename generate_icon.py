from PIL import Image, ImageDraw

def create_base_icon(target_size):
    """
    使用超取樣技術繪製一致風格的高品質圖示
    """
    factor = 8  # 8x supersampling
    canvas_size = target_size * factor
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    w, h = canvas_size, canvas_size
    cx, cy = w / 2, h / 2

    # 1. 統一的比例參數 (所有尺寸一致，保持設計感)
    padding = w * 0.1       # 適度留白 (10%)
    radius = w * 0.22       # 圓角
    bg_color = (124, 92, 252) # #7c5cfc

    # 背景
    rect = [padding, padding, w - padding, h - padding]
    draw.rounded_rectangle(rect, radius=radius, fill=bg_color)

    # 2. 白色圖示
    arrow_color = (255, 255, 255)
    
    # 箭頭參數
    # 箭頭寬度 (左右展開的寬度)
    arrow_wing_w = w * 0.25 
    # 箭頭高度
    arrow_h = h * 0.14
    # 箭頭距離中心垂直間距
    gap = h * 0.12

    # 中間橫線
    # 這裡調整為「跟箭頭寬度一致」或視覺協調
    # 由於箭頭是三角形，這裡讓橫線長度等於箭頭底邊寬度稍短一點，顯得精緻
    line_total_width = arrow_wing_w * 1.6 
    line_thickness = h * 0.08  # 適中的線條粗細

    # (A) 上箭頭
    top_y_base = cy - gap
    top_y_tip = top_y_base - arrow_h
    draw.polygon([
        (cx, top_y_tip),
        (cx - arrow_wing_w, top_y_base),
        (cx + arrow_wing_w, top_y_base)
    ], fill=arrow_color)

    # (B) 下箭頭
    bottom_y_base = cy + gap
    bottom_y_tip = bottom_y_base + arrow_h
    draw.polygon([
        (cx, bottom_y_tip),
        (cx - arrow_wing_w, bottom_y_base),
        (cx + arrow_wing_w, bottom_y_base)
    ], fill=arrow_color)

    # (C) 中間橫線 (從左到右)
    # 使用 rounded line 看起來更圓潤
    draw.line(
        [(cx - line_total_width / 2, cy), (cx + line_total_width / 2, cy)],
        fill=arrow_color,
        width=int(line_thickness)
    )

    # 3. 高品質縮小
    return img.resize((target_size, target_size), resample=Image.LANCZOS)

def create_icon_file(filename="icon.ico"):
    """產生包含所有標準尺寸的 ICO"""
    sizes = [256, 128, 64, 48, 32, 24, 16]
    images = []

    print("正在產生高品質圖示...")
    for s in sizes:
        img = create_base_icon(s)
        images.append(img)
    
    images[0].save(
        filename, 
        format='ICO', 
        sizes=[(i.width, i.height) for i in images], 
        append_images=images[1:]
    )
    print(f"✅ Icon generated: {filename}")

if __name__ == "__main__":
    create_icon_file()
