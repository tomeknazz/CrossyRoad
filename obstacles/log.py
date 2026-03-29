from libs.libs import *


class Log(QGraphicsPixmapItem):
    def __init__(self, y_pos, speed, direction):
        super().__init__()
        self.speed = speed
        self.direction = direction

        pixmap = QPixmap("log.png")
        scaled_pixmap = pixmap.scaled(CELL_SIZE * 3, CELL_SIZE, Qt.AspectRatioMode.IgnoreAspectRatio)
        self.setPixmap(scaled_pixmap)

        if self.direction == 1:
            self.setPos(-self.pixmap().width(), y_pos)
        else:
            self.setPos(SCENE_WIDTH, y_pos)

        self.debug_rect = QGraphicsRectItem(self.boundingRect(), self)
        # Czerwona ramka o grubości 2 pikseli
        self.debug_rect.setPen(QPen(QColor(Qt.GlobalColor.red), DEBUG_RECTANGLE_WIDTH))
        self.debug_rect.setVisible(False)

        logger.log("Log init (speed,direction,y_pos): " + str(self.speed) + " " + (
            "left" if self.direction == -1 else "right") + " " + str(y_pos))

    def update_position(self):
        self.moveBy(self.speed * self.direction, 0)
        if self.direction == 1 and self.pos().x() > SCENE_WIDTH:
            self.setPos(-self.pixmap().width(), self.pos().y())
        elif self.direction == -1 and self.pos().x() < -self.pixmap().width():
            self.setPos(SCENE_WIDTH, self.pos().y())
