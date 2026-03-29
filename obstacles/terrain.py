from libs.libs import *


class TerrainLane(QGraphicsRectItem):

    def __init__(self, y_pos, terrain_type):
        super().__init__(0, 0, SCENE_WIDTH, CELL_SIZE)
        self.setPos(0, y_pos)
        self.setZValue(-5)  # Zawsze pod spodem
        self.terrain_type = terrain_type

        if terrain_type == "grass":
            self.setBrush(QBrush(QColor(Qt.GlobalColor.darkGreen)))
        elif terrain_type == "road":
            self.setBrush(QBrush(QColor(Qt.GlobalColor.darkGray)))
        elif terrain_type == "river":
            self.setBrush(QBrush(QColor(Qt.GlobalColor.blue)))
        logger.log("TerrainLane init (terrain_type, y_pos): " + str(self.terrain_type) + " " + str(y_pos))

        self.setPen(QPen(Qt.PenStyle.NoPen))
