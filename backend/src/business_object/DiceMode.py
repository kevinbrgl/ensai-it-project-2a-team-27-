from business_object.game_mode import GameMode
from business_object.player import Player  
from business_object.game import Game
from datetime import datetime
import random

class DiceMode(GameMode):
    """Classe représentant le mode de jeu "Lancer de dés"."""

    def play(self, player1: Player, player2: Player) -> Game:
        """
        Joue une partie de lancer de dés entre deux joueurs et retourne l'objet Game correspondant.
        Le gagnant est déterminé aléatoirement.
        """


        result_p1 = random.randint(1, 6)
        result_p2 = random.randint(1, 6)
        winner = player1 if result_p1 > result_p2 else player2 if result_p2 > result_p1 else None
        winner_name = winner.username if winner else "Égalité"

        return Game(
            player1=player1,
            player2=player2,
            game_mode="Dice",
            winner=winner,
            description=f"Résultat du lancer de dés : {result_p1} vs {result_p2} - Gagnant : {winner_name}",
            timestamp=datetime.now(),
         )   