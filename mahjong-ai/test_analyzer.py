import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from mahjong_analyzer import MahjongAnalyzer

def test_analyzer():
    analyzer = MahjongAnalyzer()
    
    test_cases = [
        ["一万", "二万", "三万", "四万", "五万", "六万", "七万", "八万", "九万", "一筒", "二筒", "三筒", "四筒"],
        ["一万", "一万", "二万", "三万", "五万", "五万", "五万", "七万", "八万", "九万", "东", "东", "发"],
        ["二万", "三万", "四万", "五万", "六万", "七万", "八筒", "八筒", "九筒", "一条", "三条", "五条", "七条"],
        ["一万", "一万", "二万", "二万", "三万", "三万", "四万", "五万", "六万", "七筒", "八筒", "九筒", "东"],
        ["一万", "二万", "三万", "四万", "五万", "六万", "七筒", "七筒", "八筒", "八筒", "九筒", "九筒", "东"]
    ]
    
    for i, hand in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"测试用例 {i+1}:")
        print(f"手牌: {' '.join(hand)}")
        print(f"{'='*60}")
        
        result = analyzer.analyze_hand(hand)
        
        if 'error' in result:
            print(f"错误: {result['error']}")
            continue
        
        print(f"当前向听数: {result['current_shanten']}")
        print("\n推荐打牌顺序:")
        
        for j, rec in enumerate(result['recommendations'][:3]):
            print(f"\n{j+1}. 打 {rec['discard']}")
            print(f"   向听数: {rec['shanten']}")
            print(f"   听牌数: {rec['waiting_count']}张")
            if rec['waiting_tiles']:
                print(f"   听牌: {', '.join(rec['waiting_tiles'])}")

if __name__ == '__main__':
    test_analyzer()