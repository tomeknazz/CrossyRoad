from libs.libs import *
from obstacles.car import Car
from obstacles.lilypad import Lilypad
from obstacles.log import Log
from obstacles.terrain import TerrainLane
from obstacles.tree import Tree



class EntityFactory:
    @staticmethod
    def create_entity(entity_type, x=0, y=0, **kwargs):
        if entity_type == "car":
            return Car(y, kwargs.get("speed"), kwargs.get("direction"))
        elif entity_type == "log":
            return Log(y, kwargs.get("speed"), kwargs.get("direction"))
        elif entity_type == "tree":
            return Tree(x, y)
        elif entity_type == "lilypad":
            return Lilypad(x, y)
        elif entity_type == "lane":
            return TerrainLane(y, kwargs.get("terrain_type"))
        else:
            raise ValueError(f"Nieznany typ obiektu: {entity_type}")
