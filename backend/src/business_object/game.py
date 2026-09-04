from datetime import datetime
from typing import Optional
from business_object.player import Player


class Game:
    def __init__(
        self,
        player1: Player,
        player2: Player,
        game_mode: str,
        description: str,
        timestamp: datetime,
        id_game: Optional[int] = None,
        winner: Optional[Player] = None,
    ):
        self.id_game = id_game
        self.player1 = player1
        self.player2 = player2
        self.game_mode = game_mode
        self.winner = winner
        self.description = description
        self.timestamp = timestamp

    def __str__(self):
        winner_name = self.winner.username if self.winner else "No winner"
        return(
                f"{self.game_mode} between {self.player1.username} and" 
                f" {self.player2.username} at {self.timestamp}. Winner: {winner_name}."
            )