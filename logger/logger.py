from libs.libs import *


class Logger:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def log(self, msg):
        if self.enabled:
            print(time.strftime("%H:%M:%S"), msg)
