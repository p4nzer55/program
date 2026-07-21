import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from mahjong_analyzer import MahjongAnalyzer
from gui import MahjongGUI

def main():
    analyzer = MahjongAnalyzer()
    gui = MahjongGUI(analyzer)
    gui.run()

if __name__ == '__main__':
    main()