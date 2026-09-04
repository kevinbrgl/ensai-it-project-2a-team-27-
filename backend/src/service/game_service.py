from fastapi import HTTPException

from dao.player_dao import PlayerDao
from utils.log_utils import log
from business_object.GameModeFactory import GameModeFactory
from business_object.ScoringStrategy import ScoringStrategy


class GameService:
    """Service that manages games."""

    @log
    def play(self, id_player: int, id_opponent: int, game_mode: str, **kwargs) -> dict:
        if id_player == id_opponent:
            raise HTTPException(status_code=400, detail="Two different players required")

        player_dao = PlayerDao()
        p1 = player_dao.find_by_id(id_player)
        p2 = player_dao.find_by_id(id_opponent)

        if not p1 or not p2:
            raise HTTPException(status_code=404, detail="Player not found")

        # 1. Obtenir le mode de jeu
        mode = GameModeFactory.get_mode(game_mode)

        # 2. Exécuter le jeu (stocké dans un objet Game)
        game = mode.play(p1, p2)

        # 3. Mettre à jour les scores Elo
        ScoringStrategy.update_player_ratings(game)

        # 4. Sauvegarder les joueurs
        player_dao.update(p1)
        player_dao.update(p2)

        # 5. Gérer le nom du gagnant en toute sécurité
        winner_name = game.winner.username if game.winner else "Draw"

        return {
            "player1": p1.username,
            "player2": p2.username,
            "description": game.description,
            "winner": winner_name,
            "new_elo1": p1.elo,
            "new_elo2": p2.elo,
        }