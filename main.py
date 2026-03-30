from libs.libs import *
from obstacles.car import Car
from obstacles.lilypad import Lilypad
from obstacles.log import Log
from obstacles.terrain import TerrainLane
from obstacles.tree import Tree
from player.player import Player


class GameWindow(QGraphicsView):
    def __init__(self, difficulty):
        super().__init__()
        self.config = self.load_configuration("config.json")
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
        # Co ile sekund zwiększamy trudność
        self.time_to_increase_difficulty = self.config["time_to_increase_difficulty"]

        self.cars = []
        self.logs = []
        self.lanes = []
        self.trees = []
        self.lilypads = []

        self.load_ahead_rows = self.config["forward_rows"]
        self.keep_behind_rows = self.config["backward_rows"]

        # Śledzi, na jakiej wysokości (Y) wygenerowaliśmy ostatni pas mapy
        self.highest_generated_y = CELL_SIZE * 2
        self.safe_x = (SCENE_WIDTH // 2) // CELL_SIZE * CELL_SIZE
        self.map_layout_index = 0

        self.consecutive_rivers = 0
        self.max_consecutive_rivers = self.config["max_consecutive_rivers"]
        self.consecutive_roads = 0
        self.max_consecutive_roads = self.config["max_consecutive_roads"]
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
        # Decyzja co 50ms
        self.ai_timer.start(self.config["ai_timer_ms"])

        # Generujemy początkową mapę
        self.generate_map_chunk(self.config["initial_chunk_load_size"])
        # System usuwania itp
        self.manage_world()

        self.timer = QTimer()
        self.timer.timeout.connect(self.game_loop)
        self.timer.start(16)

    def load_configuration(self, filepath="config.json"):
        # domyslne
        default_config = {
            "time_to_increase_difficulty": 30,
            "forward_rows": 25,
            "backward_rows": 10,
            "max_consecutive_rivers": 3,
            "max_consecutive_roads": 5,
            "ai_timer_ms": 50,
            "initial_chunk_load_size": 20,
            "generate_missing_map_count": 5,
            "initial_safe_row_count": 3,
            "car_easy_min_speed": 1,
            "car_easy_max_speed": 4,
            "car_medium_min_speed": 2,
            "car_medium_max_speed": 9,
            "car_hard_min_speed": 4,
            "car_hard_max_speed": 13,
            "log_easy_min_speed": 1,
            "log_easy_max_speed": 4,
            "log_medium_hard_min_speed": 2,
            "log_medium_hard_max_speed": 9,
            "lily_min_try_count": 3,
            "lily_max_try_count": 7,
            "tree_min_try_count": 2,
            "tree_max_try_count": 7,
            "use_custom_map": False,
            "custom_map_layout": ["grass", "grass", "road", "road", "road", "grass", "river", "river", "river", "grass"],
            "log_spawn_chance": 0.7
        }

        config = default_config.copy()

        # wczyttywanie
        try:
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    user_config = json.load(f)
                for key, value in user_config.items():
                    # Walidacja: klucz musi istnieć ORAZ typ zmiennej musi się zgadzać (np. int == int)
                    if key in config and isinstance(value, type(config[key])):
                        config[key] = value
                    else:
                        logger.log(f"Config - Nieprawidłowy klucz lub typ danych dla '{key}'")
                logger.log("Wczytano konfigurację z pliku")
            else:
                logger.log("Brak pliku config.json.")
        except Exception as e:
            logger.log(f"Błąd wczytywania config.json: {e}.")

        return config

    def save_game(self):
        state = {
            "player": {"x": self.player.pos().x(), "y": self.player.pos().y()},
            "highest_generated_y": self.highest_generated_y,
            "safe_x": self.safe_x,
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
        self.safe_x = state.get("safe_x", (SCENE_WIDTH // 2) // CELL_SIZE * CELL_SIZE)
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
            self.highest_generated_y -= CELL_SIZE
            y = self.highest_generated_y
            prev_safe_x = self.safe_x

            if self.config.get("use_custom_map", False):
                layout = self.config.get("custom_map_layout", ["grass"])
                t_type = layout[self.map_layout_index % len(layout)]
                self.map_layout_index += 1
            else:
                # Losowy generator
                if y > -CELL_SIZE * self.config["initial_safe_row_count"]:
                    t_type = "grass"
                else:
                    t_type = random.choice(terrain_types)
                    if t_type == "river" and self.consecutive_rivers >= self.max_consecutive_rivers:
                        t_type = random.choice(["grass", "road"])
                    elif t_type == "road" and self.consecutive_roads >= self.max_consecutive_roads:
                        t_type = random.choice(["grass", "river"])

           # bezpieczna sciezka
            if y <= -CELL_SIZE * self.config["initial_safe_row_count"]:
                shift = random.choice([-CELL_SIZE, 0, CELL_SIZE])
                self.safe_x += shift
                self.safe_x = max(0, min(SCENE_WIDTH - CELL_SIZE, self.safe_x))

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
            lane = EntityFactory.create_entity("lane", y=y, terrain_type=t_type)
            self.scene.addItem(lane)
            self.lanes.append(lane)

            # Dodajemy przeszkody w zależności od typu
            if t_type == "road":
                if self.difficulty == "easy":
                    speed = random.randrange(self.config["car_easy_min_speed"], self.config["car_easy_max_speed"])
                elif self.difficulty == "medium":
                    speed = random.randrange(self.config["car_medium_min_speed"], self.config["car_medium_max_speed"])
                else:
                    speed = random.randrange(self.config["car_hard_min_speed"], self.config["car_hard_max_speed"])
                car = EntityFactory.create_entity("car", y=y, speed=speed)
                self.scene.addItem(car)
                self.cars.append(car)

            elif t_type == "river":

                if random.random() > self.config["log_spawn_chance"]:
                    # safe lilia
                    safe_lily = EntityFactory.create_entity("lilypad", x=self.safe_x, y=y)
                    self.scene.addItem(safe_lily)
                    self.lilypads.append(safe_lily)

                    if self.safe_x != prev_safe_x:
                        safe_lily_bridge = Lilypad(prev_safe_x, y)
                        safe_lily_bridge = EntityFactory.create_entity("lilypad", x=prev_safe_x, y=y)
                        self.scene.addItem(safe_lily_bridge)
                        self.lilypads.append(safe_lily_bridge)

                    trees_below_x = []
                    for tree in self.trees:
                        if tree.pos().y() == y + CELL_SIZE:
                            trees_below_x.append(tree.pos().x())

                    '''# tworzenie lilii
                    for _ in range(random.randint(3, 7)):
                        lily_x = random.randint(0, (SCENE_WIDTH // CELL_SIZE) - 1) * CELL_SIZE
                        # nie kladziemy tam gdzie juz jest
                        if lily_x != self.safe_x and lily_x != prev_safe_x and lily_x not in trees_below_x:
                            lily = Lilypad(lily_x, y)
                            self.scene.addItem(lily)
                            self.lilypads.append(lily)'''

                    target_lily_count = random.randint(self.config["lily_min_try_count"], self.config["lily_max_try_count"])
                    all_possible_x = [col * CELL_SIZE for col in range(SCENE_WIDTH // CELL_SIZE)]

                    available_x = []
                    for x in all_possible_x:
                        if x != self.safe_x and x != prev_safe_x and x not in trees_below_x:
                            available_x.append(x)

                    actual_lily_count = min(target_lily_count, len(available_x))

                    chosen_x_positions = random.sample(available_x, actual_lily_count)

                    for lily_x in chosen_x_positions:
                        lily = EntityFactory.create_entity("lilypad", x=lily_x, y=y)
                        self.scene.addItem(lily)
                        self.lilypads.append(lily)

                else:
                    # wymuszenie przeciwnego kierunku i predkosci kłód przy generowaniu rzek pod rząd
                    if self.consecutive_rivers > 1:
                        direction = self.prev_river_direction * -1
                        if self.difficulty == "easy":
                            speeds = [s for s in range(self.config["log_easy_min_speed"], self.config["log_easy_max_speed"]) if s != self.prev_river_direction]
                        else:
                            speeds = [s for s in range(self.config["log_medium_hard_min_speed"], self.config["log_medium_hard_max_speed"]) if s != self.prev_river_direction]
                        speed = random.choice(speeds) if speeds else 2
                    else:
                        direction = random.choice([1, -1])
                        if self.difficulty == "easy":
                            speed = random.randrange(self.config["log_easy_min_speed"], self.config["log_easy_max_speed"])
                        else:
                            speed = random.randrange(self.config["log_medium_hard_min_speed"], self.config["log_medium_hard_max_speed"])

                    self.prev_river_direction = direction
                    self.prev_river_speed = speed

                    # Tworzymy 2 kłody na jednym pasie rzeki
                    log1 = EntityFactory.create_entity("log", y=y, speed=speed, direction=direction)
                    log2 = EntityFactory.create_entity("log", y=y, speed=speed, direction=direction)
                    # Rozsuwamy je od siebie
                    log2.setPos(log1.pos().x() + (SCENE_WIDTH // 2) + 50 * direction * random.random(), y)

                    self.scene.addItem(log1)
                    self.scene.addItem(log2)
                    self.logs.append(log1)
                    self.logs.append(log2)

            elif t_type == "grass" and y < -CELL_SIZE:
                occupied_x = [self.safe_x, prev_safe_x]
                # nie dodawaj drzew jesli pod spodem lub nad jest lilia
                for lily in self.lilypads:
                    if int(lily.pos().y()) == y - CELL_SIZE:
                        occupied_x.append(int(lily.pos().x()))
                    if int(lily.pos().y()) == y + CELL_SIZE:
                        occupied_x.append(int(lily.pos().x()))

                for i in range(random.randint(self.config["tree_min_try_count"], self.config["tree_max_try_count"])):
                    tree_x = random.randint(0, (SCENE_WIDTH // CELL_SIZE) - 1) * CELL_SIZE
                    if tree_x not in occupied_x and (tree_x - CELL_SIZE) not in occupied_x and (tree_x + CELL_SIZE) not in occupied_x:
                        tree = EntityFactory.create_entity("tree", x=tree_x, y=y)
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
        self.safe_x = (SCENE_WIDTH // 2) // CELL_SIZE * CELL_SIZE
        self.map_layout_index = 0
        self.frame_counter = 0
        self.start_time = time.time()
        self.difficulty = self.difficulty_initial

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
            self.generate_map_chunk(self.config["generate_missing_map_count"])
            logger.log("Generated missing map ahead")

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
        elif event.key() == Qt.Key.Key_F5:
            logger.log("Wywołano Hot Reload konfiguracji")
            # Wczytanie nowych parametrów z pliku
            self.config = self.load_configuration("config.json")

            # Aktualizacja systemów w tle
            self.ai_timer.setInterval(self.config.get("ai_timer_ms", 100))
            self.max_consecutive_rivers = self.config.get("max_consecutive_rivers", 3)
            self.max_consecutive_roads = self.config.get("max_consecutive_roads", 5)
            self.time_to_increase_difficulty = self.config.get("time_to_increase_difficulty", 30)

            self.reset_game()

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

    def is_valid_target(self, target_x, target_y):
        target_x = int(target_x)
        target_y = int(target_y)

        # 1. Najpierw sprawdzamy, czy w ogóle da się tam wejść (czy nie ma tam drzewa/wody/auta)
        if not self.is_safe(target_x, target_y):
            return False

        # 2. --- UNIWERSALNY WYKRYWACZ ŚLEPYCH ZAUŁKÓW ---
        # Symulujemy, jakie opcje ruchu miałby bot, GDYBY wszedł na to pole
        up = self.is_safe(target_x, target_y - CELL_SIZE)
        left = self.is_safe(target_x - CELL_SIZE, target_y)
        right = self.is_safe(target_x + CELL_SIZE, target_y)

        # Jeśli z tego pola NIE DA SIĘ wyjść do przodu ani w boki, to jest to pułapka!
        # Bot odrzuci to pole jako "nieprawidłowe" i w ogóle na nie nie wejdzie.
        if not (up or left or right):
            return False

        return True

    def is_safe(self, target_x, target_y):
        # Ograniczenie wyjścia poza ekran
        if target_x < 0 or target_x > SCENE_WIDTH - CELL_SIZE:
            return False
        # kolizja z drzewem
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

                    # [ZMIANA] Dodajemy 10 pikseli marginesu, żeby zniwelować mikro-ruchy kłody
                    if log_left - 10 <= player_center <= log_right + 10:
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
            return True

        return True

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
            if int(lane.pos().y()) == py:
                current_terrain = lane.terrain_type
                break

        on_lilypad = False
        if current_terrain == "river":
            for lily in self.lilypads:
                if int(lily.pos().y()) == py and int(lily.pos().x()) == px:
                    on_lilypad = True
                    break

        # PRIORYTET 1: EWAKUACJA
        danger_from_edge = False
        if current_terrain == "river":
            if px < CELL_SIZE * 1.5 or px > SCENE_WIDTH - CELL_SIZE * 2.5:
                danger_from_edge = True

        if not current_safe or danger_from_edge:
            if up_safe:
                self.handle_action("up")
            elif left_safe and px > SCENE_WIDTH // 2:
                self.handle_action("left")
            elif right_safe and px < SCENE_WIDTH // 2:
                self.handle_action("right")
            elif left_safe:
                self.handle_action("left")
            elif right_safe:
                self.handle_action("right")
            elif down_safe:
                self.handle_action("down")
            return


        # Szukanie ścieżki

        target_gap_x = None
        min_dist = 999999999999

        for check_x in range(0, SCENE_WIDTH, CELL_SIZE):
            if self.is_valid_target(check_x, py - CELL_SIZE):
                dist = abs(check_x - px)

                # Karę za zablokowany kierunek ignorujemy na kłodzie
                if current_terrain != "river" or on_lilypad:
                    if check_x < px and not left_safe:
                        dist += 1000
                    elif check_x > px and not right_safe:
                        dist += 1000

                if not self.is_safe(check_x, py - 2 * CELL_SIZE):
                    dist += 500

                if dist < min_dist:
                    min_dist = dist
                    target_gap_x = check_x

        # PRIORYTET 2: RUCH W GÓRĘ
        if up_safe and self.is_valid_target(px, py - CELL_SIZE):
            if current_terrain == "river" and not on_lilypad and target_gap_x is not None and target_gap_x != px:
                pass
            else:
                self.handle_action("up")
                return

        # PRIORYTET 3: RUCH W BOK DO CELU
        if target_gap_x is not None:
            if target_gap_x < px:
                if left_safe:
                    self.handle_action("left")
                    return
                elif (current_terrain != "river" or on_lilypad) and down_safe:
                    self.handle_action("down")
                    return
                elif current_terrain == "river" and not on_lilypad:
                    return

            elif target_gap_x > px:
                if right_safe:
                    self.handle_action("right")
                    return
                elif (current_terrain != "river" or on_lilypad) and down_safe:
                    self.handle_action("down")
                    return
                elif current_terrain == "river" and not on_lilypad:
                    return

        # PRIORYTET 4: ŚRODKOWANIE
        center_x = (SCENE_WIDTH // 2) - (CELL_SIZE // 2)
        if px > center_x:
            if left_safe:
                self.handle_action("left")
            elif right_safe:
                self.handle_action("right")
            elif down_safe:
                self.handle_action("down")
        else:
            if right_safe:
                self.handle_action("right")
            elif left_safe:
                self.handle_action("left")
            elif down_safe:
                self.handle_action("down")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow("EaSy")
    window.setWindowTitle("Crossy Road")
    window.show()
    sys.exit(app.exec())
