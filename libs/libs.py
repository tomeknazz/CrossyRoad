import json
import random
import sys
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QTransform
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem

from logger.logger import Logger

CELL_SIZE = 40
SCENE_WIDTH = 600
SCENE_HEIGHT = 900
logger = Logger()