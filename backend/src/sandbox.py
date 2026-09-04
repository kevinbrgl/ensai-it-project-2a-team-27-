from business_object.player import Player
from business_object.GameModeFactory import GameModeFactory
from business_object.ScoringStrategy import ScoringStrategy

# 1. Création de deux joueurs de test
p1 = Player(username="Jacky", elo=1000, email="jacky@test.com")
p2 = Player(username="Jackie", elo=1000, email="jackie@test.com")

print("=== AVANT LE MATCH ===")
print(f"{p1.username} Elo: {p1.elo}")
print(f"{p2.username} Elo: {p2.elo}\n")

# 2. On choisit un mode via la Factory ("dice" ou "coinflip")
mode_jeu = "Dice"  # Change par "coinflip" pour tester l'autre mode !
mode = GameModeFactory.get_mode(mode_jeu)

# 3. Lancement de la partie
game = mode.play(p1, p2)

# 4. Mise à jour des scores avec la stratégie
ScoringStrategy.update_player_ratings(game)

# 5. Affichage des résultats
print("=== DÉROULEMENT DU MATCH ===")
print(f"Mode de jeu : {game.game_mode}")
print(f"Description : {game.description}")
print(f"Résumé      : {game}\n")

print("=== APRÈS LE MATCH ===")
print(f"{p1.username} Elo: {p1.elo}")
print(f"{p2.username} Elo: {p2.elo}")
