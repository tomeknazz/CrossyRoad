from libs.libs import *


class Tree(QGraphicsPixmapItem):
    def __init__(self, x, y):
        super().__init__()
        pixmap = QPixmap("tree.png")
        self.setPixmap(pixmap.scaled(CELL_SIZE, CELL_SIZE, Qt.AspectRatioMode.IgnoreAspectRatio))
        self.setPos(x, y)

        self.debug_rect = QGraphicsRectItem(self.boundingRect(), self)
        self.debug_rect.setPen(QPen(QColor(Qt.GlobalColor.red), 2))
        self.debug_rect.setVisible(False)
