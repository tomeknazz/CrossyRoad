from libs.libs import *

class Player(QGraphicsPixmapItem):
    def __init__(self):
        super().__init__()

        pixmap = QPixmap("chicken.png")
        scaled_pixmap = pixmap.scaled(CELL_SIZE, CELL_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
        self.setPixmap(scaled_pixmap)
        self.setZValue(10)
        self.reset_position()
        logger.log("Player init")

        self.debug_rect = QGraphicsRectItem(self.boundingRect(), self)
        # Czerwona ramka o grubości 2 pikseli
        self.debug_rect.setPen(QPen(QColor(Qt.GlobalColor.red), 2))
        self.debug_rect.setVisible(False)

    def reset_position(self):
        # Startujemy zawsze z punktu (środek, 0)
        start_x = (SCENE_WIDTH // 2) - (CELL_SIZE // 2)
        start_y = 0
        self.setPos(start_x, start_y)

    def move_up(self):
        snapped_x = round(self.pos().x() / CELL_SIZE) * CELL_SIZE
        self.setPos(snapped_x, self.pos().y() - CELL_SIZE)
        logger.log("Player move_up")

    def move_down(self):
        snapped_x = round(self.pos().x() / CELL_SIZE) * CELL_SIZE
        self.setPos(snapped_x, self.pos().y() + CELL_SIZE)
        logger.log("Player move_down")

    def move_left(self):
        snapped_x = round(self.pos().x() / CELL_SIZE) * CELL_SIZE
        self.setPos(snapped_x - CELL_SIZE, self.pos().y())
        logger.log("Player move_left")

    def move_right(self):
        snapped_x = round(self.pos().x() / CELL_SIZE) * CELL_SIZE
        self.setPos(snapped_x + CELL_SIZE, self.pos().y())
        logger.log("Player move_right")
