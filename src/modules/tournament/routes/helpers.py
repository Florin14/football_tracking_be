import random
import pandas as pd
from deap import base, creator, tools, algorithms

# Constants
VALUE_WEIGHT = 0.9  # Weight for the player's value
FORM_WEIGHT = 0.1   # Weight for the player's form (performance)

def load_player_data(file_path):
    """Load player data from an Excel file."""
    df = pd.read_excel(file_path)
    players = [
        {
            "name": row['Name'],
            "value": row['Value'],
            "grades": [row['Grade1'], row['Grade2'], row['Grade3'], row['Grade4'], row['Grade5']],
            "position": row['Position']
        }
        for _, row in df.iterrows()
    ]
    return players

def select_players(players):
    """Randomly select 14 players (2 goalkeepers, 12 others)."""
    goalkeepers = [p for p in players if p["position"] == "Goalkeeper"]
    non_goalkeepers = [p for p in players if p["position"] != "Goalkeeper"]

    selected_goalkeepers = random.sample(goalkeepers, 2)
    selected_non_goalkeepers = random.sample(non_goalkeepers, 12)

    return selected_goalkeepers + selected_non_goalkeepers

def normalize_values(players):
    """Normalize player values and grades."""
    values = [p["value"] / 100.0 for p in players]
    grades = [sum(p["grades"]) / len(p["grades"]) / 10.0 for p in players]
    return values, grades

def identify_high_value_players(players):
    """Identify players with value > 88."""
    return [(i, p["name"], p["value"]) for i, p in enumerate(players) if p["value"] > 88]

def validate_teams(individual, player_positions, team1_high_value, team2_high_value):
    """Ensure each team has at least one goalkeeper and an equal number of defenders."""
    team1, team2 = [i for i, g in enumerate(individual) if g == 0], [i for i, g in enumerate(individual) if g == 1]

    if sum(player_positions[i] == 'Goalkeeper' for i in team1) < 1 or sum(player_positions[i] == 'Goalkeeper' for i in team2) < 1:
        return False

    if sum(player_positions[i] == 'Defender' for i in team1) != sum(player_positions[i] == 'Defender' for i in team2):
        return False

    if not (all(i in team1 for i in team1_high_value) and all(i in team2 for i in team2_high_value)):
        return False

    return True

def evaluate_teams(individual, normalized_values, normalized_grades, player_positions, team1_high_value, team2_high_value):
    """Evaluate how balanced the teams are based on their values."""
    if not validate_teams(individual, player_positions, team1_high_value, team2_high_value):
        return 100,

    team1_value = sum((VALUE_WEIGHT * normalized_values[i]) + (FORM_WEIGHT * normalized_grades[i]) for i, g in enumerate(individual) if g == 0)
    team2_value = sum((VALUE_WEIGHT * normalized_values[i]) + (FORM_WEIGHT * normalized_grades[i]) for i, g in enumerate(individual) if g == 1)

    return abs(team1_value - team2_value),

def genetic_algorithm(selected_players):
    """Run the Genetic Algorithm to generate balanced teams."""
    normalized_values, normalized_grades = normalize_values(selected_players)
    high_value_players = identify_high_value_players(selected_players)

    team1_high_value = [i for i, _, _ in high_value_players if i % 2 == 0]
    team2_high_value = [i for i, _, _ in high_value_players if i % 2 == 1]

    player_positions = [p["position"] for p in selected_players]
    player_names = [p["name"] for p in selected_players]

    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()
    toolbox.register("attr_bool", random.randint, 0, 1)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_bool, n=len(selected_players))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    toolbox.register("evaluate", lambda ind: evaluate_teams(ind, normalized_values, normalized_grades, player_positions, team1_high_value, team2_high_value))
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutFlipBit, indpb=0.1)
    toolbox.register("select", tools.selTournament, tournsize=3)

    population = toolbox.population(n=100)
    for _ in range(100):
        offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.2)
        fits = list(map(toolbox.evaluate, offspring))
        for fit, ind in zip(fits, offspring):
            ind.fitness.values = fit
        population = toolbox.select(offspring, k=len(population))

    best_individual = tools.selBest(population, k=1)[0]

    team1 = [player_names[i] for i, g in enumerate(best_individual) if g == 0]
    team2 = [player_names[i] for i, g in enumerate(best_individual) if g == 1]

    return {
        "team1": team1,
        "team2": team2,
        "balance_difference": abs(sum(normalized_values[i] for i, g in enumerate(best_individual) if g == 0) - sum(normalized_values[i] for i, g in enumerate(best_individual) if g == 1))
    }

def generate_teams(file_path):
    """Main function to generate balanced teams."""
    players = load_player_data(file_path)
    selected_players = select_players(players)
    return genetic_algorithm(selected_players)

# Example usage
if __name__ == "__main__":
    file_path = 'sambata.xlsx'
    teams = generate_teams(file_path)
    print("Team 1:", teams["team1"])
    print("Team 2:", teams["team2"])
