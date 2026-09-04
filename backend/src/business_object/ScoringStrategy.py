import os
from business_object.player import Player
from business_object.game import Game

class ScoringStrategy:
    """A class that implements the Elo rating system for two players."""

    @classmethod
    def calculate_expected_score(cls, elo_a: float, elo_b: float) -> float:
        """Calculates the probability of player A winning against player B."""
        return 1 / (1 + 10 ** ((elo_b - elo_a) / 400))

    @classmethod
    def calculate_new_ratings(cls, elo_a: float, elo_b: float, player_a_won: bool) -> tuple[int, int]:
        """Computes the new Elo ratings for two players after a match."""
        # 32 par défaut si ELO_K_FACTOR n'est pas défini
        k_factor = int(os.getenv("ELO_K_FACTOR", 32))

        score_a = 1.0 if player_a_won else 0.0
        score_b = 1.0 - score_a

        new_elo_a = round(elo_a + k_factor * (score_a - cls.calculate_expected_score(elo_a, elo_b)))
        new_elo_b = round(elo_b + k_factor * (score_b - cls.calculate_expected_score(elo_b, elo_a)))

        return new_elo_a, new_elo_b

    @classmethod
    def update_player_ratings(cls, game: Game) -> None:
        """Calculates and updates the elo attributes of the players based on a Game instance.
        No update if there is no winner (Draw).
        """
        if not game.winner:
            return

        p1 = game.player1
        p2 = game.player2

        p1.elo, p2.elo = cls.calculate_new_ratings(
            p1.elo, p2.elo, player_a_won=(p1 == game.winner)
            )