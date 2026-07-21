import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time

class MahjongGUI:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.root = tk.Tk()
        self.root.title("雀魂AI助手")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        self.is_running = False
        self.current_hand = []
        self.discarded_tiles = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top_frame, text="手牌:", font=('Arial', 12)).pack(side=tk.LEFT)
        
        self.hand_entry = ttk.Entry(top_frame, width=60, font=('Arial', 12))
        self.hand_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.hand_entry.insert(0, "一万 二万 三万 四万 五万 六万 七万 八万 九万 一筒 二筒 三筒 四筒")
        
        self.analyze_btn = ttk.Button(top_frame, text="分析", command=self.analyze_hand)
        self.analyze_btn.pack(side=tk.LEFT)
        
        self.auto_capture_btn = ttk.Button(top_frame, text="自动识别", command=self.toggle_auto_capture)
        self.auto_capture_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        hand_frame = ttk.LabelFrame(main_frame, text="当前手牌", padding="10")
        hand_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.hand_display = ttk.Label(hand_frame, text="", font=('Arial', 14))
        self.hand_display.pack()
        
        result_frame = ttk.LabelFrame(main_frame, text="AI分析结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, font=('Arial', 11))
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="状态: 就绪", font=('Arial', 10))
        self.status_label.pack(side=tk.LEFT)
        
        self.shanten_label = ttk.Label(status_frame, text="当前向听数: -", font=('Arial', 10))
        self.shanten_label.pack(side=tk.RIGHT)
    
    def analyze_hand(self):
        hand_str = self.hand_entry.get().strip()
        hand_tiles = [t.strip() for t in hand_str.split() if t.strip()]
        
        if not hand_tiles:
            self._show_message("请输入手牌")
            return
        
        self.current_hand = hand_tiles
        self.hand_display.config(text=" ".join(hand_tiles))
        
        result = self.analyzer.analyze_hand(hand_tiles)
        
        if 'error' in result:
            self._show_message(result['error'])
            return
        
        self.shanten_label.config(text=f"当前向听数: {result['current_shanten']}")
        
        output = f"当前向听数: {result['current_shanten']}\n\n"
        output += "推荐打牌顺序:\n"
        output += "=" * 50 + "\n"
        
        for i, rec in enumerate(result['recommendations']):
            output += f"\n{i+1}. 打 {rec['discard']}\n"
            output += f"   向听数: {rec['shanten']}\n"
            output += f"   听牌数: {rec['waiting_count']}张\n"
            if rec['waiting_tiles']:
                output += f"   听牌: {', '.join(rec['waiting_tiles'])}\n"
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, output)
    
    def _show_message(self, message):
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, message)
    
    def toggle_auto_capture(self):
        if self.is_running:
            self.is_running = False
            self.auto_capture_btn.config(text="自动识别")
            self.status_label.config(text="状态: 已停止")
        else:
            self.is_running = True
            self.auto_capture_btn.config(text="停止识别")
            self.status_label.config(text="状态: 正在识别...")
            self._start_capture_thread()
    
    def _start_capture_thread(self):
        def capture_loop():
            while self.is_running:
                try:
                    self._simulate_capture()
                except Exception as e:
                    print(f"捕获错误: {e}")
                time.sleep(2)
        
        thread = threading.Thread(target=capture_loop, daemon=True)
        thread.start()
    
    def _simulate_capture(self):
        test_hands = [
            ["一万", "二万", "三万", "四万", "五万", "六万", "七万", "八万", "九万", "一筒", "二筒", "三筒", "四筒"],
            ["一万", "一万", "二万", "三万", "五万", "五万", "五万", "七万", "八万", "九万", "东", "东", "发"],
            ["二万", "三万", "四万", "五万", "六万", "七万", "八筒", "八筒", "九筒", "一条", "三条", "五条", "七条"]
        ]
        
        import random
        hand = random.choice(test_hands)
        self.hand_entry.delete(0, tk.END)
        self.hand_entry.insert(0, " ".join(hand))
        self.analyze_hand()
    
    def run(self):
        self.root.mainloop()