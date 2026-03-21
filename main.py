import random
import sys
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem
from PyQt6.QtGui import QBrush, QColor, QPen, QPixmap, QTransform

from loggger import Logger

CELL_SIZE = 40
SCENE_WIDTH = 600
SCENE_HEIGHT = 600
logger = Logger()


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
        self.moveBy(0, -CELL_SIZE)
        logger.log("Player move_up")

    def move_down(self):
        self.moveBy(0, CELL_SIZE)
        logger.log("Player move_down")

    def move_left(self):
        self.moveBy(-CELL_SIZE, 0)
        logger.log("Player move_left")

    def move_right(self):
        self.moveBy(CELL_SIZE, 0)
        logger.log("Player move_right")


# KLASY PRZESZKÓD I TŁA

class Car(QGraphicsPixmapItem):
    def __init__(self, y_pos, speed):
        super().__init__()
        self.speed = speed
        self.direction = 1 if random.choice([True, False]) else -1
        colors = [1,2,3]
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
        self.debug_rect.setPen(QPen(QColor(Qt.GlobalColor.red), 2))
        self.debug_rect.setVisible(False)

        logger.log("Car init (speed,direction,y_pos): " + str(self.speed) + " " + ("left" if self.direction == -1 else "right") + " " + str(y_pos))

    def update_position(self):
        self.moveBy(self.speed * self.direction, 0)
        if self.direction == 1 and self.pos().x() > SCENE_WIDTH:
            self.setPos(-self.pixmap().width(), self.pos().y())
        elif self.direction == -1 and self.pos().x() < -self.pixmap().width():
            self.setPos(SCENE_WIDTH, self.pos().y())


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
        self.debug_rect.setPen(QPen(QColor(Qt.GlobalColor.red), 2))
        self.debug_rect.setVisible(False)

        logger.log("Log init (speed,direction,y_pos): " + str(self.speed) + " " + ("left" if self.direction == -1 else "right") + " " + str(y_pos))

    def update_position(self):
        self.moveBy(self.speed * self.direction, 0)
        if self.direction == 1 and self.pos().x() > SCENE_WIDTH:
            self.setPos(-self.pixmap().width(), self.pos().y())
        elif self.direction == -1 and self.pos().x() < -self.pixmap().width():
            self.setPos(SCENE_WIDTH, self.pos().y())


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


class GameWindow(QGraphicsView):
    def __init__(self, difficulty):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Wyłączamy suwaki, żeby wyglądało jak gra, a nie dokument
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedSize(SCENE_WIDTH, SCENE_HEIGHT)
        self.difficulty = difficulty.lower()
        logger.log("GameWindow init (difficulty): " + str(self.difficulty))

        self.player = Player()
        self.scene.addItem(self.player)
        self.start_time = time.time()
        self.time_to_increase_difficulty = 30  # Co ile sekund zwiększamy trudność

        self.cars = []
        self.logs = []
        self.lanes = []

        self.load_ahead_rows = 25
        self.keep_behind_rows = 10

        # Śledzi, na jakiej wysokości (Y) wygenerowaliśmy ostatni pas mapy
        self.highest_generated_y = CELL_SIZE * 2
        self.debug_mode = False

        # AI
        self.ai_mode = False
        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self.make_ai_decision)
        # AI podejmuje decyzję co 200ms
        self.ai_timer.start(10)

        # Generujemy początkową mapę (np. 30 rzędów w górę)
        self.generate_map_chunk(30)
        # Dorób od razu okno świata w zależności od pozycji gracza
        self.manage_world()

        self.timer = QTimer()
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(16)

    def generate_map_chunk(self, rows):
        terrain_types = ["grass", "road", "river"]
        previous_terrain = ""

        if time.time() - self.start_time > self.time_to_increase_difficulty and self.difficulty != "hard":
            if self.difficulty == "easy":
                self.difficulty = "medium"
            elif self.difficulty == "medium":
                self.difficulty = "hard"
            self.start_time = time.time()  # Resetujemy timer zwiększania trudności
            logger.log("Increasing difficulty level: " + self.difficulty)

        for _ in range(rows):
            # Przesuwamy wskaźnik budowy w górę
            self.highest_generated_y -= CELL_SIZE
            y = self.highest_generated_y

            # Zawsze robimy pierwszych kilka rzędów bezpiecznych (trawa)
            if y > -CELL_SIZE * 3:
                t_type = "grass"
            else:
                t_type = random.choice(terrain_types)
                while t_type == previous_terrain:
                    t_type = random.choice(terrain_types)
                previous_terrain = t_type

            # Rysujemy tło pasa
            lane = TerrainLane(y, t_type)
            self.scene.addItem(lane)
            self.lanes.append(lane)

            # Dodajemy przeszkody w zależności od typu
            if t_type == "road":
                if self.difficulty == "easy":
                    speed = random.randrange(1, 4)
                elif self.difficulty == "medium":
                    speed = random.randrange(2, 9)
                else:
                    speed = random.randrange(4, 13)
                car = Car(y, speed)
                self.scene.addItem(car)
                self.cars.append(car)

            elif t_type == "river":
                if self.difficulty == "easy":
                    speed = random.randint(1, 3)
                else:
                    speed = random.randrange(1, 9)
                direction = random.choice([1, -1])
                # Tworzymy 2 kłody na jednym pasie rzeki dla łatwiejszej gry
                log1 = Log(y, speed, direction)
                log2 = Log(y, speed, direction)
                # Rozsuwamy je od siebie
                log2.setPos(log1.pos().x() + (SCENE_WIDTH // 2) + 50*direction * random.random(), y)

                self.scene.addItem(log1)
                self.scene.addItem(log2)
                self.logs.append(log1)
                self.logs.append(log2)

    def reset_game(self):
        logger.log("Resetting game")
        self.player.reset_position()
        self.centerOn(SCENE_WIDTH // 2, self.player.pos().y())
        # Czyszczenie obiektów
        for item in self.cars + self.logs + self.lanes:
            self.scene.removeItem(item)
        self.cars.clear()
        self.logs.clear()
        self.lanes.clear()
        logger.log("Removed instances")
        self.highest_generated_y = CELL_SIZE * 2
        # generuj od nowa po restarcie
        logger.log("Starting world generation")
        self.generate_map_chunk(30)
        self.manage_world()

    def manage_world(self):
        player_y = self.player.pos().y()

        # jeśli brakuje pasów do przodu to dogeneruj
        top_target_y = int((player_y - (self.load_ahead_rows * CELL_SIZE)) // CELL_SIZE) * CELL_SIZE
        while self.highest_generated_y > top_target_y:
            # 5 rzedów zeby nie bylo za czesto duplikatów rodzajów terenu koło siebie
            self.generate_map_chunk(5)
            logger.log("Generating missing map ahead")


        # usuń elementy, które są z tylu
        keep_y = int((player_y + (self.keep_behind_rows * CELL_SIZE)) // CELL_SIZE) * CELL_SIZE

        # Lanes
        lanes_to_remove = [lane for lane in self.lanes if lane.pos().y() > keep_y]
        for lane in lanes_to_remove:
            self.scene.removeItem(lane)
            self.lanes.remove(lane)
            logger.log("Removed lane:" + str(len(lanes_to_remove)))

        # Cars
        cars_to_remove = [car for car in self.cars if car.pos().y() > keep_y]
        for car in cars_to_remove:
            self.scene.removeItem(car)
            self.cars.remove(car)
            logger.log("Removed car:" + str(len(cars_to_remove)))

        # Logs
        logs_to_remove = [log for log in self.logs if log.pos().y() > keep_y]
        for log in logs_to_remove:
            self.scene.removeItem(log)
            self.logs.remove(log)
            logger.log("Removed log:" + str(len(logs_to_remove)))

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode
        logger.log("Toggled debug")
        for item in self.scene.items():
            if hasattr(item, "debug_rect"):
                item.debug_rect.setVisible(self.debug_mode)

    def keyPressEvent(self, event):
        # strzałki lub wasd
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self.player.move_up()
        elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self.player.move_down()
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.player.move_left()
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.player.move_right()
        elif event.key() == Qt.Key.Key_H:
            self.toggle_debug()
        # Dodaj to pod obsługą klawisza 'H'
        elif event.key() == Qt.Key.Key_P:
            self.ai_mode = not self.ai_mode
            logger.log(f"Tryb AI ustawiony na: {self.ai_mode}")

        # organiczenie żeby kurczak nie uciekł poza ekran
        if self.player.pos().x() < 0: self.player.setPos(0, self.player.pos().y())
        if self.player.pos().x() > SCENE_WIDTH - CELL_SIZE: self.player.setPos(SCENE_WIDTH - CELL_SIZE,
                                                                               self.player.pos().y())

    def game_loop(self):
        # "kamera" na graczu
        self.centerOn(SCENE_WIDTH // 2, self.player.pos().y() - (SCENE_HEIGHT // 4))

        self.manage_world()

        for car in self.cars:
            car.update_position()
        for log in self.logs:
            log.update_position()

        # kolizje
        collisions = self.scene.collidingItems(self.player)
        in_river = False
        on_log = None

        for item in collisions:
            if isinstance(item, Car):
                logger.log("Collision with car detected")
                self.reset_game()
                return
            elif isinstance(item, TerrainLane) and item.terrain_type == "river":
                in_river = True
            elif isinstance(item, Log):
                on_log = item

        if in_river:
            if on_log:
                self.player.moveBy(on_log.speed * on_log.direction, 0)
                # Jesli gracz wypłynął na kłodzie poza ekran to reset
                if self.player.pos().x() > SCENE_WIDTH - CELL_SIZE / 2 or self.player.pos().x() <= -CELL_SIZE / 2:
                    logger.log("Player tried to swim out of bounds")
                    self.reset_game()
            else:
                logger.log("Player jumped into water")
                self.reset_game()

    def is_safe(self, target_x, target_y):
        # Ograniczenie wyjścia poza ekran
        if target_x < 0 or target_x > SCENE_WIDTH - CELL_SIZE:
            return False

        # typ terenu
        terrain_type = "grass"  # domyślnie
        for lane in self.lanes:
            if lane.pos().y() == target_y:
                terrain_type = lane.terrain_type
                break

        # obsluga rzeki
        if terrain_type == "river":
            player_center = target_x + CELL_SIZE / 2
            for log in self.logs:
                if log.pos().y() == target_y:
                    log_left = log.pos().x()
                    log_right = log.pos().x() + log.pixmap().width()
                    # Sprawdzamy, czy środek gracza wylądowałby na tej kłodzie
                    if log_left <= player_center <= log_right:
                        return True
            return False  # Brak kłody = zle

        # obsluga ukliocy
        elif terrain_type == "road":
            player_left = target_x
            player_right = target_x + CELL_SIZE

            for car in self.cars:
                if car.pos().y() == target_y:
                    car_left = car.pos().x()
                    car_right = car.pos().x() + car.pixmap().width()

                    # margines bledu
                    # auto przesunie się do przodu o 1 kratkę
                    if car.direction == 1:  # Jedzie w prawo
                        if car_right + CELL_SIZE > player_left and car_left < player_right:
                            return False  # Zbyt blisko z lewej
                    else:  # Jedzie w lewo
                        if car_left - CELL_SIZE < player_right and car_right > player_left:
                            return False  # Zbyt blisko z prawej
            return True  # Brak nadjeżdżających aut na tej kratce

        return True  # Trawa - zawsze bezpieczna

    def make_ai_decision(self):
        if not self.ai_mode:
            return

        px = self.player.pos().x()
        py = self.player.pos().y()
        up_safe = self.is_safe(px, py - CELL_SIZE)
        down_safe = self.is_safe(px, py + CELL_SIZE)
        left_safe = self.is_safe(px - CELL_SIZE, py)
        right_safe = self.is_safe(px + CELL_SIZE, py)
        current_safe = self.is_safe(px, py)

        current_terrain = "grass"
        for lane in self.lanes:
            if lane.pos().y() == py:
                current_terrain = lane.terrain_type
                break

        #PRIORYTET 1: EWAKUACJA
        danger_from_edge = False
        if current_terrain == "river":
            # Jeśli zbliżamy się do krawędzi ekranu na rzece
            if px < CELL_SIZE * 1.5 or px > SCENE_WIDTH - CELL_SIZE * 2.5:
                danger_from_edge = True

        # Jeśli stoimy na ulicy i zagraża nam auto
        if not current_safe or danger_from_edge:
            logger.log("AI: ZAGROŻENIE!")
            if up_safe:
                self.player.move_up()
            elif down_safe:
                self.player.move_down()
            # Jeśli tył i przód zajęte, uciekaj w bok do środka mapy
            elif left_safe and px > SCENE_WIDTH // 2:
                self.player.move_left()
            elif right_safe and px < SCENE_WIDTH // 2:
                self.player.move_right()
            # Ostatnia deska ratunku
            elif left_safe:
                self.player.move_left()
            elif right_safe:
                self.player.move_right()
            return

        # PRIORYTET 2: ŚRODKOWANIE
        # Idealny środek uwzględniający kratki
        center_x = (SCENE_WIDTH // 2) - (CELL_SIZE // 2)
        dist_to_center = abs(px - center_x)

        dist_left = abs((px - CELL_SIZE) - center_x)
        dist_right = abs((px + CELL_SIZE) - center_x)
        # Jeśli jesteśmy na trawie i nie jesteśmy na środku
        if current_terrain == "grass":
            #zeby nei chodził lewo-prawo w kółko bez sensu
            if px > center_x and dist_left < dist_to_center and left_safe:
                self.player.move_left()
                return
            # to samo dla prawej strony
            elif px < center_x and dist_right < dist_to_center and right_safe:
                self.player.move_right()
                return

        # PRIORYTET 3: RUCH DO PRZODU
        if up_safe:
            self.player.move_up()
            return

        # PRIORYTET 4: KROK W BOK PODCZAS CZEKANIA
        # Jeśli nie możemy iść w górę to centrujemy
        if px > center_x and dist_left < dist_to_center and left_safe:
            self.player.move_left()
            return
        elif px < center_x and dist_right < dist_to_center and right_safe:
            self.player.move_right()
            return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow("EaSy")
    window.setWindowTitle("Crossy Road")
    window.show()
    sys.exit(app.exec())
