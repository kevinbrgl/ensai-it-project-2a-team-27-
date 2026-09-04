from abc import ABC, abstractmethod
from business_object.game import Game
from business_object.player import Player


class GameMode(ABC):
    """Classe abstraite servant d'interface pour tous les modes de jeu."""

    @abstractmethod
    def play(self, player1: Player, player2: Player) -> Game:
        """
        Joue une partie entre deux joueurs et retourne l'objet Game correspondant.
        """
        pass