import sys
import random
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPen

CELL_SIZE = 40
SCENE_WIDTH = 600
SCENE_HEIGHT = 600


class Player(QGraphicsRectItem):
    def __init__(self):
        super().__init__(0, 0, CELL_SIZE, CELL_SIZE)
        self.setBrush(QBrush(QColor(Qt.GlobalColor.yellow)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setZValue(10)
        self.reset_position()

    def reset_position(self):
        # Startujemy zawsze z punktu (środek, 0)
        start_x = (SCENE_WIDTH // 2) - (CELL_SIZE // 2)
        start_y = 0
        self.setPos(start_x, start_y)

    def move_up(self): self.moveBy(0, -CELL_SIZE)

    def move_down(self): self.moveBy(0, CELL_SIZE)

    def move_left(self): self.moveBy(-CELL_SIZE, 0)

    def move_right(self): self.moveBy(CELL_SIZE, 0)


# --- KLASY PRZESZKÓD I TŁA ---

class Car(QGraphicsRectItem):
    def __init__(self, y_pos, speed):
        super().__init__(0, 0, CELL_SIZE * 2, CELL_SIZE)
        self.speed = speed
        colors = [Qt.GlobalColor.red, Qt.GlobalColor.magenta, Qt.GlobalColor.cyan]
        self.setBrush(QBrush(QColor(random.choice(colors))))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setPos(-CELL_SIZE * 2, y_pos)

    def update_position(self):
        self.moveBy(self.speed, 0)
        if self.pos().x() > SCENE_WIDTH:
            self.setPos(-self.rect().width(), self.pos().y())


class Log(QGraphicsRectItem):
    def __init__(self, y_pos, speed, direction):
        super().__init__(0, 0, CELL_SIZE * 3, CELL_SIZE)
        self.speed = speed
        self.direction = direction
        self.setBrush(QBrush(QColor(139, 69, 19)))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        if self.direction == 1:
            self.setPos(-self.rect().width(), y_pos)
        else:
            self.setPos(SCENE_WIDTH, y_pos)

    def update_position(self):
        self.moveBy(self.speed * self.direction, 0)
        if self.direction == 1 and self.pos().x() > SCENE_WIDTH:
            self.setPos(-self.rect().width(), self.pos().y())
        elif self.direction == -1 and self.pos().x() < -self.rect().width():
            self.setPos(SCENE_WIDTH, self.pos().y())


class TerrainLane(QGraphicsRectItem):
    """ Klasa reprezentująca tło dla pojedynczego pasa (trawa, ulica, woda) """

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

        self.setPen(QPen(Qt.PenStyle.NoPen))


# --- GŁÓWNA KLASA GRY ---

class GameWindow(QGraphicsView):
    def __init__(self):
        super().__init__()
        # Zauważ: nie podajemy już rozmiaru sceny! Pozwalamy jej rosnąć w nieskończoność.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Wyłączamy suwaki, żeby wyglądało jak gra, a nie dokument
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedSize(SCENE_WIDTH, SCENE_HEIGHT)

        self.player = Player()
        self.scene.addItem(self.player)

        self.cars = []
        self.logs = []
        self.lanes = []

        # Śledzi, na jakiej wysokości (Y) wygenerowaliśmy ostatni pas mapy
        self.highest_generated_y = CELL_SIZE * 2

        # Generujemy początkową mapę (np. 30 rzędów w górę)
        self.generate_map_chunk(30)

        self.timer = QTimer()
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(16)

    def generate_map_chunk(self, rows):
        """ Generuje nowe pasy terenu posuwając się w górę (czyli w kierunku ujemnych Y) """
        terrain_types = ["grass", "grass", "road", "road", "river", "river"]

        for _ in range(rows):
            # Przesuwamy wskaźnik budowy w górę
            self.highest_generated_y -= CELL_SIZE
            y = self.highest_generated_y

            # Zawsze robimy pierwszych kilka rzędów bezpiecznych (trawa)
            if y > -CELL_SIZE * 3:
                t_type = "grass"
            else:
                t_type = random.choice(terrain_types)

            # Rysujemy tło pasa
            lane = TerrainLane(y, t_type)
            self.scene.addItem(lane)
            self.lanes.append(lane)

            # Dodajemy przeszkody w zależności od typu
            if t_type == "road":
                speed = random.randint(2, 6)
                car = Car(y, speed)
                self.scene.addItem(car)
                self.cars.append(car)

            elif t_type == "river":
                speed = random.randint(1, 4)
                direction = random.choice([1, -1])
                # Tworzymy 2 kłody na jednym pasie rzeki dla łatwiejszej gry
                log1 = Log(y, speed, direction)
                log2 = Log(y, speed, direction)
                # Rozsuwamy je od siebie
                log2.setPos(log1.pos().x() + (SCENE_WIDTH // 2), y)

                self.scene.addItem(log1)
                self.scene.addItem(log2)
                self.logs.append(log1)
                self.logs.append(log2)

    def reset_game(self):
        print("Koniec gry! Zaczynamy od nowa.")
        self.player.reset_position()
        self.centerOn(SCENE_WIDTH // 2, self.player.pos().y())

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self.player.move_up()
        elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self.player.move_down()
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.player.move_left()
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.player.move_right()
        else:
            super().keyPressEvent(event)

        # Ograniczenie, żeby kurczak nie uciekł w lewo/prawo poza ekran
        if self.player.pos().x() < 0: self.player.setPos(0, self.player.pos().y())
        if self.player.pos().x() > SCENE_WIDTH - CELL_SIZE: self.player.setPos(SCENE_WIDTH - CELL_SIZE,
                                                                               self.player.pos().y())

    def game_loop(self):
        # 1. KAMERA - Śledzi gracza
        # Odejmujemy SCENE_HEIGHT // 4, żeby gracz był w dolnej części ekranu, a nie na środku
        self.centerOn(SCENE_WIDTH // 2, self.player.pos().y() - (SCENE_HEIGHT // 4))

        # 2. GENEROWANIE MAPY - Jeśli gracz zbliża się do końca wygenerowanej mapy, dobudowujemy ją
        if self.player.pos().y() - (SCENE_HEIGHT) < self.highest_generated_y:
            self.generate_map_chunk(10)

        # 3. RUCH PRZESZKÓD
        for car in self.cars: car.update_position()
        for log in self.logs: log.update_position()

        # 4. KOLIZJE (Tak jak w poprzedniej wersji)
        collisions = self.scene.collidingItems(self.player)
        in_river = False
        on_log = None

        for item in collisions:
            if isinstance(item, Car):
                self.reset_game()
                return
            elif isinstance(item, TerrainLane) and item.terrain_type == "river":
                in_river = True
            elif isinstance(item, Log):
                on_log = item

        if in_river:
            if on_log:
                self.player.moveBy(on_log.speed * on_log.direction, 0)
                if self.player.pos().x() < -CELL_SIZE or self.player.pos().x() > SCENE_WIDTH:
                    self.reset_game()
            else:
                self.reset_game()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow()
    window.setWindowTitle("PyQt6 Crossy Road - Generator Mapy")
    window.show()
    sys.exit(app.exec())