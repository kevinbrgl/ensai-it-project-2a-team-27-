from business_object.game_mode import GameMode
from business_object.DiceMode import DiceMode
from business_object.CoinFlipMode import CoinFlipMode
from business_object.player import Player
from business_object.game import Game



class GameModeFactory:

    @classmethod
    def get_mode(cls, game_mode: str) -> GameMode:
        """
        Retourne l'objet GameMode correspondant au mode de jeu spécifié.

        Args:
            game_mode (str): Le nom du mode de jeu ("Dice" ou "Coinflip").
        Returns:
            GameMode: Un instance de la classe GameMode correspondant au mode de jeu spécifié.
        Raises:
            ValueError: Si le mode de jeu spécifié n'est pas reconnu.
        """

        mode_clean = game_mode.strip().lower()

        if mode_clean == "dice":
            from business_object.DiceMode import DiceMode
            return DiceMode()
        elif mode_clean == "coinflip":
            from business_object.CoinFlipMode import CoinFlipMode
            return CoinFlipMode()
        else:
            raise ValueError(f"Mode de jeu inconnu : {game_mode}")
