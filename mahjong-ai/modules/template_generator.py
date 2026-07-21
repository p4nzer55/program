import cv2
import numpy as np
import os

TILE_WIDTH = 50
TILE_HEIGHT = 70
TILE_THICKNESS = 3

SUITS = {
    'wan': {'symbol': '万', 'color': (0, 0, 255), 'range': 9},
    'tong': {'symbol': '筒', 'color': (0, 128, 0), 'range': 9},
    'tiao': {'symbol': '条', 'color': (139, 69, 19), 'range': 9},
}

HONORS = {
    'feng': {'symbols': ['东', '南', '西', '北'], 'color': (0, 0, 0)},
    'yuan': {'symbols': ['中', '发', '白'], 'color': [(255, 0, 0), (0, 128, 0), (128, 128, 128)]},
}

def create_tile_image(value, suit):
    img = np.ones((TILE_HEIGHT, TILE_WIDTH, 3), dtype=np.uint8) * 255
    
    cv2.rectangle(img, (2, 2), (TILE_WIDTH-3, TILE_HEIGHT-3), (0, 0, 0), TILE_THICKNESS)
    
    if suit in SUITS:
        config = SUITS[suit]
        text = f"{value}{config['symbol']}"
        cv2.putText(img, text, (5, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, config['color'], 2)
        cv2.putText(img, text, (5, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.4, config['color'], 1)
    elif suit == 'feng':
        text = HONORS['feng']['symbols'][value-1]
        cv2.putText(img, text, (12, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.8, HONORS['feng']['color'], 3)
    elif suit == 'yuan':
        text = HONORS['yuan']['symbols'][value-1]
        color = HONORS['yuan']['color'][value-1]
        cv2.putText(img, text, (12, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 3)
    
    return img

def generate_all_templates(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    for suit, config in SUITS.items():
        for value in range(1, config['range'] + 1):
            img = create_tile_image(value, suit)
            filename = f"{suit}_{value}.png"
            cv2.imwrite(os.path.join(output_dir, filename), img)
    
    for value in range(1, 5):
        img = create_tile_image(value, 'feng')
        filename = f"feng_{value}.png"
        cv2.imwrite(os.path.join(output_dir, filename), img)
    
    for value in range(1, 4):
        img = create_tile_image(value, 'yuan')
        filename = f"yuan_{value}.png"
        cv2.imwrite(os.path.join(output_dir, filename), img)

if __name__ == '__main__':
    generate_all_templates('/workspace/mahjong-ai/templates')
    print("模板生成完成！")