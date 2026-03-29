from libs.libs import *


class Car(QGraphicsPixmapItem):
    def __init__(self, y_pos, speed, direction=None):
        super().__init__()
        self.speed = speed
        self.direction = direction if direction is not None else (1 if random.choice([True, False]) else -1)
        colors = [1, 2, 3]
        color = random.choice(colors)
        pixmap = QPixmap(f"car{color}.png")
        scaled_pixmap = pixmap.scaled(CELL_SIZE * 2, CELL_SIZE, Qt.AspectRatioMode.IgnoreAspectRatio)

        transform = QTransform()
        if self.direction == 1:
            transform.rotate(90)
        else:
            transform.rotate(-90)
        scaled_pixmap = scaled_pixmap.transformed(transform)
        scaled_pixmap = scaled_pixmap.scaled(CELL_SIZE * 2, CELL_SIZE, Qt.AspectRatioMode.IgnoreAspectRatio)
        self.setPixmap(scaled_pixmap)
        self.setPos(-CELL_SIZE * 2, y_pos)

        self.debug_rect = QGraphicsRectItem(self.boundingRect(), self)
        # Czerwona ramka o grubości 2 pikseli
        self.debug_rect.setPen(QPen(QColor(Qt.GlobalColor.red), DEBUG_RECTANGLE_WIDTH))
        self.debug_rect.setVisible(False)

        logger.log("Car init (speed,direction,y_pos): " + str(self.speed) + " " + (
            "left" if self.direction == -1 else "right") + " " + str(y_pos))

    def update_position(self):
        self.moveBy(self.speed * self.direction, 0)
        if self.direction == 1 and self.pos().x() > SCENE_WIDTH:
            self.setPos(-self.pixmap().width(), self.pos().y())
        elif self.direction == -1 and self.pos().x() < -self.pixmap().width():
            self.setPos(SCENE_WIDTH, self.pos().y())
