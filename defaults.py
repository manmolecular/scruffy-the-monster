class Config:
    SQLALCHEMY_URL: str = "sqlite:///./app.db"


class RaceConditionRate:
    ATTACK_TIME: float = 0.5


class UserDefaults:
    HEALTH: int = 100
    STRENGTH: int = 20
    HITS: int = 5


class MonsterDefaults:
    HEALTH: int = 100
    STRENGTH: int = 30
    HITS: int = 9999
    MONSTERNAME: str = "scruffy"
