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
TIME_TO_INCREASE_DIFFICULTY = 30
FORWARD_ROWS = 25
BACKWARD_ROWS = 10
MAX_CONSECUTIVE_RIVERS = 3
MAX_CONSECUTIVE_ROADS = 5
AI_TIMER_MS = 50
INITIAL_CHUNK_LOAD_SIZE = 20
DEBUG_RECTANGLE_WIDTH = 2
INITIAL_SAFE_ROW_COUNT = 3
# Car speeds
CAR_EASY_MIN_SPEED = 1
CAR_EASY_MAX_SPEED = 4
CAR_MEDIUM_MIN_SPEED = 2
CAR_MEDIUM_MAX_SPEED = 9
CAR_HARD_MIN_SPEED = 4
CAR_HARD_MAX_SPEED = 13
# Log speeds
LOG_EASY_MIN_SPEED = 1
LOG_EASY_MAX_SPEED = 4
LOG_MEDIUM_HARD_MIN_SPEED = 2
LOG_MEDIUM_HARD_MAX_SPEED = 9
# Tree place try count
TREE_MIN_TRY_COUNT = 2
TREE_MAX_TRY_COUNT = 7
# Lily count
LILY_MIN_TRY_COUNT = 3
LILY_MAX_TRY_COUNT = 7
# Generate missing map
GENERATE_MISSING_MAP_COUNT = 5

logger = Logger()
