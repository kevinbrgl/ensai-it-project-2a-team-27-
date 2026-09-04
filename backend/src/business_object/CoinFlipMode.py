from business_object.game_mode import GameMode
from business_object.player import Player
from business_object.game import Game
from datetime import datetime
import secrets

class CoinFlipMode(GameMode):
    """Classe représentant le mode de jeu "Pile ou Face"."""

    def play(self, player1: Player, player2: Player) -> Game:
        """
        Joue une partie de pile ou face entre deux joueurs et retourne l'objet Game correspondant.
        Le gagnant est déterminé aléatoirement.
        """

        result = secrets.choice(["heads", "tails"])
        winner = player1 if result == "heads" else player2

        return Game(
            player1=player1,
            player2=player2,
            game_mode="Coinflip",
            winner=winner,
            description=f"  Résultat du jeu : {result}",
            timestamp=datetime.now(),
        )