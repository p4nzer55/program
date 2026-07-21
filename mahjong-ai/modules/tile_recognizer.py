import cv2
import numpy as np
import os

TILE_MAP = {
    'wan_1': '一万', 'wan_2': '二万', 'wan_3': '三万', 'wan_4': '四万', 'wan_5': '五万',
    'wan_6': '六万', 'wan_7': '七万', 'wan_8': '八万', 'wan_9': '九万',
    'tong_1': '一筒', 'tong_2': '二筒', 'tong_3': '三筒', 'tong_4': '四筒', 'tong_5': '五筒',
    'tong_6': '六筒', 'tong_7': '七筒', 'tong_8': '八筒', 'tong_9': '九筒',
    'tiao_1': '一条', 'tiao_2': '二条', 'tiao_3': '三条', 'tiao_4': '四条', 'tiao_5': '五条',
    'tiao_6': '六条', 'tiao_7': '七条', 'tiao_8': '八条', 'tiao_9': '九条',
    'feng_1': '东', 'feng_2': '南', 'feng_3': '西', 'feng_4': '北',
    'yuan_1': '中', 'yuan_2': '发', 'yuan_3': '白'
}

class TileRecognizer:
    def __init__(self, template_dir):
        self.templates = {}
        self.load_templates(template_dir)
    
    def load_templates(self, template_dir):
        for filename in os.listdir(template_dir):
            if filename.endswith('.png'):
                template_name = filename[:-4]
                template_path = os.path.join(template_dir, filename)
                template = cv2.imread(template_path, cv2.IMREAD_COLOR)
                if template is not None:
                    self.templates[template_name] = template
    
    def recognize_tile(self, tile_img, threshold=0.7):
        tile_img_gray = cv2.cvtColor(tile_img, cv2.COLOR_BGR2GRAY)
        
        best_match = None
        best_score = 0
        
        for template_name, template in self.templates.items():
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            if tile_img_gray.shape[0] < template_gray.shape[0] or \
               tile_img_gray.shape[1] < template_gray.shape[1]:
                template_gray = cv2.resize(template_gray, (tile_img_gray.shape[1], tile_img_gray.shape[0]))
            
            result = cv2.matchTemplate(tile_img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            
            if max_val > best_score and max_val > threshold:
                best_score = max_val
                best_match = template_name
        
        if best_match:
            return TILE_MAP.get(best_match, best_match), best_score
        return None, 0
    
    def detect_tiles_in_region(self, img, region, tile_width=50, tile_height=70, gap=5):
        x, y, w, h = region
        tiles = []
        
        num_tiles = int((w + gap) / (tile_width + gap))
        start_x = x
        
        for i in range(num_tiles):
            tile_x = start_x + i * (tile_width + gap)
            if tile_x + tile_width > x + w:
                break
            
            tile_region = img[y:y+tile_height, tile_x:tile_x+tile_width]
            if tile_region.size > 0:
                tile_name, score = self.recognize_tile(tile_region)
                if tile_name:
                    tiles.append((tile_name, score, tile_x, y))
        
        return tiles
    
    def detect_discarded_tiles(self, img, start_y, row_height=80, num_rows=4):
        discarded = []
        
        for row in range(num_rows):
            y = start_y + row * row_height
            region = (0, y, img.shape[1], row_height)
            tiles = self.detect_tiles_in_region(img, region)
            discarded.extend(tiles)
        
        return discarded