class Contracts():
    def __init__(self, data):
        self.faction = data["faction"]
        self.type = data["type"]
        self.deadline = data["deadline"]
        self.goods = data["goods"]
        self.destination = data["destination"]
        self.owing = data["owing"]



class Agent():
    def __init__(self, data):
        pass