from obstacles.car import Car
from obstacles.tree import Tree
from obstacles.terrain import TerrainLane
from obstacles.log import Log
from obstacles.lilypad import Lilypad
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


class GameWindow(QGraphicsView):
    def __init__(self, difficulty):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Wyłączamy suwaki
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedSize(SCENE_WIDTH, SCENE_HEIGHT)
        self.difficulty_initial = difficulty.lower()
        self.difficulty = difficulty.lower()
        logger.log("GameWindow init (difficulty): " + str(self.difficulty))

        self.player = Player()
        self.scene.addItem(self.player)
        self.start_time = time.time()
        self.time_to_increase_difficulty = 30  # Co ile sekund zwiększamy trudność

        self.cars = []
        self.logs = []
        self.lanes = []
        self.trees = []
        self.lilypads = []

        self.load_ahead_rows = 25
        self.keep_behind_rows = 10

        # Śledzi, na jakiej wysokości (Y) wygenerowaliśmy ostatni pas mapy
        self.highest_generated_y = CELL_SIZE * 2

        self.consecutive_rivers = 0
        self.max_consecutive_rivers = 3
        self.consecutive_roads = 0
        self.max_consecutive_roads = 5
        self.prev_river_direction = 1
        self.prev_river_speed = 2

        self.debug_mode = False

        # System replay
        self.run_seed = random.randint(0, 999999)
        random.seed(self.run_seed)
        self.frame_counter = 0
        self.action_log = []
        self.saved_action_log = []
        self.is_replaying = False

        # AI
        self.ai_mode = False
        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self.make_ai_decision)
        # AI podejmuje decyzję co 50ms
        self.ai_timer.start(50)

        # Generujemy początkową mapę (np. 30 rzędów w górę)
        self.generate_map_chunk(30)
        # Dorób od razu okno świata w zależności od pozycji gracza
        self.manage_world()

        self.timer = QTimer()
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(16)

    def save_game(self):
        state = {
            "player": {"x": self.player.pos().x(), "y": self.player.pos().y()},
            "highest_generated_y": self.highest_generated_y,
            "difficulty": self.difficulty,
            "lanes": [{"y": lane.pos().y(), "type": lane.terrain_type} for lane in self.lanes],
            "cars": [{"y": car.pos().y(), "x": car.pos().x(), "speed": car.speed, "direction": car.direction} for car in
                     self.cars],
            "logs": [{"y": log.pos().y(), "x": log.pos().x(), "speed": log.speed, "direction": log.direction} for log in
                     self.logs],
            "trees": [{"x": tree.pos().x(), "y": tree.pos().y()} for tree in self.trees],
            "lilypads": [{"x": lily.pos().x(), "y": lily.pos().y()} for lily in self.lilypads]
        }
        with open("savegame.json", "w") as f:
            json.dump(state, f)
        logger.log("Gra zapisana w pliku savegame.json")

    def load_game(self):
        try:
            with open("savegame.json", "r") as f:
                state = json.load(f)
        except FileNotFoundError:
            logger.log("Gra nie była zapisane")
            return

        # Wyłączenie trybów automatycznych
        self.is_replaying = False
        self.ai_mode = False

        # Czyszczenie sceny
        for item in self.cars + self.logs + self.lanes + self.trees + self.lilypads:
            self.scene.removeItem(item)
        self.cars.clear()
        self.logs.clear()
        self.lanes.clear()
        self.trees.clear()
        self.lilypads.clear()

        # Odtwarzanie stanu
        self.difficulty = state["difficulty"]
        self.highest_generated_y = state["highest_generated_y"]
        self.player.setPos(state["player"]["x"], state["player"]["y"])

        for l in state["lanes"]:
            lane = TerrainLane(l["y"], l["type"])
            self.scene.addItem(lane)
            self.lanes.append(lane)

        for c in state["cars"]:
            car = Car(c["y"], c["speed"], c["direction"])
            car.setPos(c["x"], c["y"])
            self.scene.addItem(car)
            self.cars.append(car)

        for log_data in state["logs"]:
            log = Log(log_data["y"], log_data["speed"], log_data["direction"])
            log.setPos(log_data["x"], log_data["y"])
            self.scene.addItem(log)
            self.logs.append(log)

        for t_data in state.get("trees", []):
            tree = Tree(t_data["x"], t_data["y"])
            self.scene.addItem(tree)
            self.trees.append(tree)

        for l_data in state.get("lilypads", []):
            lily = Lilypad(l_data["x"], l_data["y"])
            self.scene.addItem(lily)
            self.lilypads.append(lily)

        # centrowanie kamery
        self.centerOn(SCENE_WIDTH // 2, self.player.pos().y() - (SCENE_HEIGHT // 4))
        logger.log("Gra wczytana")

    def handle_action(self, action):
        # Ignoruj ręczne wejścia, jeśli trwa powtórka
        if self.is_replaying:
            return

        # Zapisz akcję i dokładną klatkę, w której została wykonana
        self.action_log.append((self.frame_counter, action))
        self.execute_action(action)

    def execute_action(self, action):
        current_x = self.player.pos().x()
        snapped_x = round(current_x / CELL_SIZE) * CELL_SIZE

        target_x = self.player.pos().x()
        target_y = self.player.pos().y()

        if action == "up":
            target_y -= CELL_SIZE
        elif action == "down":
            target_y += CELL_SIZE
        elif action == "left":
            target_x -= CELL_SIZE
        elif action == "right":
            target_x += CELL_SIZE

        for tree in self.trees:
            # gracz spływając na kłodzie może nie być idealnie w "kratce"
            if tree.pos().y() == target_y and tree.pos().x() == target_x:
                logger.log("Ruch zablokowany przez drzewo")
                return

        if action == "up":
            self.player.move_up()
        elif action == "down":
            self.player.move_down()
        elif action == "left":
            self.player.move_left()
        elif action == "right":
            self.player.move_right()

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
                # Ograniczenie nie wiadomo ile spawnu pod rząd
                if t_type == "river" and self.consecutive_rivers >= self.max_consecutive_rivers:
                    t_type = random.choice(["grass", "road"])
                elif t_type == "road" and self.consecutive_roads >= self.max_consecutive_roads:
                    t_type = random.choice(["grass", "river"])
            if t_type == "river":
                self.consecutive_rivers += 1
                self.consecutive_roads = 0
            elif t_type == "road":
                self.consecutive_roads += 1
                self.consecutive_rivers = 0
            else:
                self.consecutive_rivers = 0
                self.consecutive_roads = 0

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

                if random.random() > 0.7:
                    # tworzenie lilii
                    for _ in range(random.randint(3, 8)):
                        lily_x = random.randint(0, (SCENE_WIDTH // CELL_SIZE) - 1) * CELL_SIZE
                        lily = Lilypad(lily_x, y)
                        self.scene.addItem(lily)
                        self.lilypads.append(lily)
                else:
                    # wymuszenie przeciwnego kierunku i predkosci kłód przy generowaniu rzek pod rząd
                    if self.consecutive_rivers > 1:
                        direction = self.prev_river_direction * -1
                        if self.difficulty == "easy":
                            speeds = [s for s in range(1, 4) if s != self.prev_river_direction]
                        else:
                            speeds = [s for s in range(2, 9) if s != self.prev_river_direction]
                        speed = random.choice(speeds) if speeds else 2
                    else:
                        direction = random.choice([1, -1])
                        if self.difficulty == "easy":
                            speed = random.randrange(1, 3)
                        else:
                            speed = random.randrange(2, 9)

                    self.prev_river_direction = direction
                    self.prev_river_speed = speed

                    # Tworzymy 2 kłody na jednym pasie rzeki dla łatwiejszej gry
                    log1 = Log(y, speed, direction)
                    log2 = Log(y, speed, direction)
                    # Rozsuwamy je od siebie
                    log2.setPos(log1.pos().x() + (SCENE_WIDTH // 2) + 50 * direction * random.random(), y)

                    self.scene.addItem(log1)
                    self.scene.addItem(log2)
                    self.logs.append(log1)
                    self.logs.append(log2)

            elif t_type == "grass" and y < -CELL_SIZE:
                for i in range(random.randint(2,9)):
                    tree_x=random.randint(0, (SCENE_WIDTH // CELL_SIZE) - 1) * CELL_SIZE
                    tree = Tree(tree_x, y)
                    self.scene.addItem(tree)
                    self.trees.append(tree)

    def reset_game(self, start_replay=False):
        logger.log("Resetting game")

        # Czyszczenie obiektów
        for item in self.cars + self.logs + self.lanes + self.trees + self.lilypads:
            self.scene.removeItem(item)
        self.cars.clear()
        self.logs.clear()
        self.lanes.clear()
        self.trees.clear()
        self.lilypads.clear()
        logger.log("Removed instances")

        self.highest_generated_y = CELL_SIZE * 2
        self.frame_counter = 0
        self.start_time = time.time()
        self.difficulty = self.difficulty

        if start_replay:
            self.is_replaying = True
            random.seed(self.run_seed)
            logger.log("powtorka w toku")
        else:
            self.is_replaying = False
            self.run_seed = random.randint(0, 999999)  # Nowy ziarno
            random.seed(self.run_seed)
            self.action_log.clear()  # Czyścimy logi ruchów

        self.player.reset_position()
        self.centerOn(SCENE_WIDTH // 2, self.player.pos().y())
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

        trees_to_remove = [tree for tree in self.trees if tree.pos().y() > keep_y]
        for tree in trees_to_remove:
            self.scene.removeItem(tree)
            self.trees.remove(tree)

        lilypads_to_remove = [lilypad for lilypad in self.lilypads if lilypad.pos().y() > keep_y]
        for lilypad in lilypads_to_remove:
            self.scene.removeItem(lilypad)
            self.lilypads.remove(lilypad)

    def toggle_debug(self):
        self.debug_mode = not self.debug_mode
        logger.log("Toggled debug")
        for item in self.scene.items():
            if hasattr(item, "debug_rect"):
                item.debug_rect.setVisible(self.debug_mode)

    def keyPressEvent(self, event):
        # strzałki lub wasd
        if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self.handle_action("up")
        elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self.handle_action("down")
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.handle_action("left")
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.handle_action("right")
        elif event.key() == Qt.Key.Key_H:
            self.toggle_debug()
        elif event.key() == Qt.Key.Key_P:
            self.ai_mode = not self.ai_mode
            logger.log(f"Tryb AI : {self.ai_mode}")
        elif event.key() == Qt.Key.Key_K:
            self.save_game()  # zapis
        elif event.key() == Qt.Key.Key_L:
            self.load_game()  # odczyt
        elif event.key() == Qt.Key.Key_R:  # replay
            if not self.is_replaying and len(self.action_log) > 0:
                self.saved_action_log = self.action_log.copy()
                self.reset_game(start_replay=True)

        # organiczenie żeby kurczak nie uciekł poza ekran
        if self.player.pos().x() < 0:
            self.player.setPos(0, self.player.pos().y())
        if self.player.pos().x() > SCENE_WIDTH - CELL_SIZE:
            self.player.setPos(SCENE_WIDTH - CELL_SIZE, self.player.pos().y())
        if self.player.pos().y() > 0:
            self.player.setPos(self.player.pos().x(), 0)

    def game_loop(self):
        self.frame_counter += 1

        if self.is_replaying:
            # Odtwarzanie ruchow przyspisanych do danego czasu/kaltki
            actions_this_frame = [a for f, a in self.saved_action_log if f == self.frame_counter]
            for act in actions_this_frame:
                self.execute_action(act)

            # reset po powtorce
            if self.saved_action_log and self.frame_counter > self.saved_action_log[-1][0] + 60:
                logger.log("Koniec powtórki")
                self.reset_game(start_replay=False)
                return

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
        on_lilypad = False

        for item in collisions:
            if isinstance(item, Car):
                logger.log("Collision with car detected")
                self.reset_game()
                return
            elif isinstance(item, TerrainLane) and item.terrain_type == "river":
                in_river = True
            elif isinstance(item, Log):
                on_log = item
            elif isinstance(item, Lilypad):
                on_lilypad = True

        if in_river:
            if on_lilypad:
                pass
            elif on_log:
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
        #kolizja z drzewem
        for tree in self.trees:
            if tree.pos().y() == target_y and tree.pos().x() == target_x:
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
            for lily in self.lilypads:
                if lily.pos().y() == target_y and lily.pos().x() == target_x:
                    return True
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

        px = round(self.player.pos().x() / CELL_SIZE) * CELL_SIZE
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

        # PRIORYTET 1: EWAKUACJA
        danger_from_edge = False
        if current_terrain == "river":
            # Jeśli zbliżamy się do krawędzi ekranu na rzece
            if px < CELL_SIZE * 1.5 or px > SCENE_WIDTH - CELL_SIZE * 2.5:
                danger_from_edge = True

        # Jeśli stoimy na ulicy i zagraża nam auto
        if not current_safe or danger_from_edge:
            logger.log("AI: ZAGROŻENIE!")
            if up_safe:
                self.handle_action("up")
            elif down_safe:
                self.handle_action("down")
            # Jeśli tył i przód zajęte, uciekaj w bok do środka mapy
            elif left_safe and px > SCENE_WIDTH // 2:
                self.handle_action("left")
            elif right_safe and px < SCENE_WIDTH // 2:
                self.handle_action("right")
            # Ostatnia deska ratunku
            elif left_safe:
                self.handle_action("left")
            elif right_safe:
                self.handle_action("right")
            return

        # PRIORYTET 2: ŚRODKOWANIE
        # Idealny środek uwzględniający kratki
        center_x = (SCENE_WIDTH // 2) - (CELL_SIZE // 2)
        dist_to_center = abs(px - center_x)

        dist_left = abs((px - CELL_SIZE) - center_x)
        dist_right = abs((px + CELL_SIZE) - center_x)
        # Jeśli jesteśmy na trawie i nie jesteśmy na środku
        if current_terrain == "grass":
            # zeby nei chodził lewo-prawo w kółko bez sensu
            if px > center_x and dist_left < dist_to_center and left_safe:
                self.handle_action("left")
                return
            # to samo dla prawej strony
            elif px < center_x and dist_right < dist_to_center and right_safe:
                self.handle_action("right")
                return

        # PRIORYTET 3: RUCH DO PRZODU
        if up_safe:
            self.handle_action("up")
            return

        # PRIORYTET 4: KROK W BOK PODCZAS CZEKANIA
        # Jeśli nie możemy iść w górę to centrujemy
        if px > center_x and dist_left < dist_to_center and left_safe:
            self.handle_action("left")
            return
        elif px < center_x and dist_right < dist_to_center and right_safe:
            self.handle_action("right")
            return


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow("EaSy")
    window.setWindowTitle("Crossy Road")
    window.show()
    sys.exit(app.exec())
