import json
import random
import sys
import time
import os

CELL_SIZE = 40
SCENE_WIDTH = 600
SCENE_HEIGHT = 900
DEBUG_RECTANGLE_WIDTH = 5

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QTransform
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem

from logger.logger import Logger
logger = Logger()
from factory.factory import EntityFactory



