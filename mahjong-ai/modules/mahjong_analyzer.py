from collections import Counter

TILE_VALUES = {
    '一万': 1, '二万': 2, '三万': 3, '四万': 4, '五万': 5,
    '六万': 6, '七万': 7, '八万': 8, '九万': 9,
    '一筒': 11, '二筒': 12, '三筒': 13, '四筒': 14, '五筒': 15,
    '六筒': 16, '七筒': 17, '八筒': 18, '九筒': 19,
    '一条': 21, '二条': 22, '三条': 23, '四条': 24, '五条': 25,
    '六条': 26, '七条': 27, '八条': 28, '九条': 29,
    '东': 31, '南': 32, '西': 33, '北': 34,
    '中': 41, '发': 42, '白': 43
}

REVERSE_TILE_VALUES = {v: k for k, v in TILE_VALUES.items()}

NUMERIC_TILES = [1,2,3,4,5,6,7,8,9,11,12,13,14,15,16,17,18,19,21,22,23,24,25,26,27,28,29]
HONOR_TILES = [31,32,33,34,41,42,43]

class MahjongAnalyzer:
    def __init__(self):
        self.all_tiles = list(TILE_VALUES.values())
    
    def tile_to_value(self, tile_name):
        return TILE_VALUES.get(tile_name, 0)
    
    def value_to_tile(self, value):
        return REVERSE_TILE_VALUES.get(value, str(value))
    
    def _try_remove_groups(self, counts):
        remaining = counts.copy()
        groups = 0
        
        for t in HONOR_TILES:
            while remaining.get(t, 0) >= 3:
                remaining[t] -= 3
                groups += 1
        
        for suit_base in [0, 10, 20]:
            for v in range(1, 10):
                t = suit_base + v
                while remaining.get(t, 0) >= 3:
                    remaining[t] -= 3
                    groups += 1
            
            for v in range(1, 8):
                t1, t2, t3 = suit_base + v, suit_base + v + 1, suit_base + v + 2
                while remaining.get(t1, 0) > 0 and remaining.get(t2, 0) > 0 and remaining.get(t3, 0) > 0:
                    remaining[t1] -= 1
                    remaining[t2] -= 1
                    remaining[t3] -= 1
                    groups += 1
        
        return groups, remaining
    
    def _is_complete_hand(self, counts):
        if sum(counts.values()) != 14:
            return False
        
        for pair_tile in self.all_tiles:
            if counts.get(pair_tile, 0) < 2:
                continue
            
            temp = counts.copy()
            temp[pair_tile] -= 2
            
            groups, _ = self._try_remove_groups(temp)
            if groups == 4:
                return True
        
        return False
    
    def calculate_shanten(self, hand_values):
        counts = Counter(hand_values)
        total = sum(counts.values())
        
        if total == 14:
            return 0 if self._is_complete_hand(counts) else 1
        
        if total == 13:
            for tile in self.all_tiles:
                new_counts = counts.copy()
                new_counts[tile] += 1
                if self._is_complete_hand(new_counts):
                    return 0
            return 1
        
        max_groups = 0
        has_pair = False
        
        for pair_candidate in [None] + self.all_tiles:
            temp = counts.copy()
            
            if pair_candidate and temp.get(pair_candidate, 0) >= 2:
                temp[pair_candidate] -= 2
                current_has_pair = True
            else:
                current_has_pair = False
            
            groups, _ = self._try_remove_groups(temp)
            
            if groups > max_groups:
                max_groups = groups
                has_pair = current_has_pair
            elif groups == max_groups and current_has_pair and not has_pair:
                has_pair = current_has_pair
        
        needed_groups = (total - 2) // 3
        shanten = needed_groups - max_groups
        
        if not has_pair:
            shanten += 1
        
        return max(0, shanten)
    
    def get_waiting_tiles(self, hand_values):
        if len(hand_values) != 13:
            return []
        
        counts = Counter(hand_values)
        waiting = []
        
        for tile in self.all_tiles:
            new_counts = counts.copy()
            new_counts[tile] += 1
            if self._is_complete_hand(new_counts):
                waiting.append(tile)
        
        return sorted(list(set(waiting)))
    
    def analyze_discard(self, hand_values):
        results = []
        
        for i, tile_to_discard in enumerate(hand_values):
            new_hand = hand_values[:i] + hand_values[i+1:]
            shanten = self.calculate_shanten(new_hand)
            waiting = self.get_waiting_tiles(new_hand)
            
            results.append({
                'discard': tile_to_discard,
                'shanten': shanten,
                'waiting_count': len(waiting),
                'waiting_tiles': waiting
            })
        
        results.sort(key=lambda x: (x['shanten'], -x['waiting_count']))
        return results
    
    def analyze_hand(self, hand_tiles):
        hand_values = [self.tile_to_value(t) for t in hand_tiles if t in TILE_VALUES]
        
        if len(hand_values) < 13:
            return {'error': '手牌不足13张', 'hand': hand_tiles}
        
        current_shanten = self.calculate_shanten(hand_values[:13])
        discard_results = self.analyze_discard(hand_values[:13])
        
        results = []
        for r in discard_results[:5]:
            results.append({
                'discard': self.value_to_tile(r['discard']),
                'shanten': r['shanten'],
                'waiting_count': r['waiting_count'],
                'waiting_tiles': [self.value_to_tile(t) for t in r['waiting_tiles']]
            })
        
        return {
            'hand': hand_tiles,
            'current_shanten': current_shanten,
            'recommendations': results
        }
    
    def calculate_efficiency(self, hand_values, discarded_tiles):
        remaining_counts = {t: 4 for t in self.all_tiles}
        
        for t in hand_values:
            remaining_counts[t] -= 1
        
        for t in discarded_tiles:
            v = self.tile_to_value(t)
            if v in remaining_counts:
                remaining_counts[v] -= 1
        
        efficiency = {}
        for i, tile_to_discard in enumerate(hand_values):
            new_hand = hand_values[:i] + hand_values[i+1:]
            waiting = self.get_waiting_tiles(new_hand)
            
            effective_waiting = [t for t in waiting if remaining_counts.get(t, 0) > 0]
            efficiency[tile_to_discard] = len(effective_waiting)
        
        return efficiency