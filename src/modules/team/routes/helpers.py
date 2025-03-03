import random
import pandas as pd
from deap import base, creator, tools, algorithms

# Step 1: Read player data from Excel file
file_path = 'sambata.xlsx'  # Specify your Excel file path here
df = pd.read_excel(file_path)

# Step 2: Prepare the player dataset
players = []
for index, row in df.iterrows():
    player = {
        "name": row['Name'],
        "value": row['Value'],
        "grades": [row['Grade1'], row['Grade2'], row['Grade3'], row['Grade4'], row['Grade5']],
        "position": row['Position']
    }
    players.append(player)

# Step 3: Randomly select 14 players (including goalkeepers)
goalkeepers = [player for player in players if player["position"] == "Goalkeeper"]
defenders = [player for player in players if player["position"] == "Defender"]
non_goalkeepers = [player for player in players if player["position"] != "Goalkeeper"]

# Select 2 goalkeepers and 12 other players
selected_goalkeepers = random.sample(goalkeepers, 2)
selected_non_goalkeepers = random.sample(non_goalkeepers, 12)

# Final selected players: 14 total (2 goalkeepers, 12 others)
selected_players = selected_goalkeepers + selected_non_goalkeepers

# Step 4: Prepare data for the algorithm
player_values = [player["value"] for player in selected_players]
player_names = [player["name"] for player in selected_players]
player_grades = [player["grades"] for player in selected_players]
player_positions = [player["position"] for player in selected_players]

# Constants for weighting
VALUE_WEIGHT = 0.9  # Weight for the player's value
FORM_WEIGHT = 0.1   # Weight for the player's form (performance)

# Normalize form and value
def get_normalized_values():
    normalized_values = [player["value"] / 100.0 for player in selected_players]  # Normalize values to [0, 1]
    normalized_grades = [sum(player["grades"]) / len(player["grades"]) / 10.0 for player in selected_players]  # Normalize grades to [0, 1]
    return normalized_values, normalized_grades

# Compute normalized values once and store them
normalized_values, normalized_grades = get_normalized_values()

# Identify players with value > 88
high_value_players = [(i, player_names[i], player_values[i]) for i in range(len(selected_players)) if player_values[i] > 88]

# Evenly split high-value players between teams
team1_high_value = [high_value_players[i][0] for i in range(len(high_value_players)) if i % 2 == 0]
team2_high_value = [high_value_players[i][0] for i in range(len(high_value_players)) if i % 2 == 1]

# Function to check if teams have at least one goalkeeper and the same number of defenders
def validate_teams(individual):
    team1_indices = [i for i, gene in enumerate(individual) if gene == 0]
    team2_indices = [i for i, gene in enumerate(individual) if gene == 1]

    team1_goalkeepers = sum(1 for i in team1_indices if player_positions[i] == 'Goalkeeper')
    team2_goalkeepers = sum(1 for i in team2_indices if player_positions[i] == 'Goalkeeper')

    team1_defenders = sum(1 for i in team1_indices if player_positions[i] == 'Defender')
    team2_defenders = sum(1 for i in team2_indices if player_positions[i] == 'Defender')

    # Ensure each team has at least one goalkeeper and the same number of defenders
    if team1_goalkeepers < 1 or team2_goalkeepers < 1 or team1_defenders != team2_defenders:
        return False

    # Ensure high-value players are evenly split
    if not (all(i in team1_indices for i in team1_high_value) and all(i in team2_indices for i in team2_high_value)):
        return False

    return True

# Evaluate the teams
def evaluate_teams(individual):
    if not validate_teams(individual):
        return 100,  # Penalize invalid team splits

    team1_value = sum((VALUE_WEIGHT * normalized_values[i]) + (FORM_WEIGHT * normalized_grades[i]) for i in range(len(individual)) if individual[i] == 0)
    team2_value = sum((VALUE_WEIGHT * normalized_values[i]) + (FORM_WEIGHT * normalized_grades[i]) for i in range(len(individual)) if individual[i] == 1)

    return abs(team1_value - team2_value),  # The lower the difference, the better

# Step 5: Set up Genetic Algorithm
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()
toolbox.register("attr_bool", random.randint, 0, 1)
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_bool, n=len(selected_players))
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

toolbox.register("evaluate", evaluate_teams)
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", tools.mutFlipBit, indpb=0.1)
toolbox.register("select", tools.selTournament, tournsize=3)

# Run the Genetic Algorithm
population = toolbox.population(n=100)
NGEN = 100
CXPB, MUTPB = 0.5, 0.2

for gen in range(NGEN):
    offspring = algorithms.varAnd(population, toolbox, cxpb=CXPB, mutpb=MUTPB)
    fits = list(map(toolbox.evaluate, offspring))
    for fit, ind in zip(fits, offspring):
        ind.fitness.values = fit
    population = toolbox.select(offspring, k=len(population))

best_individual = tools.selBest(population, k=1)[0]

team1 = [player_names[i] for i, gene in enumerate(best_individual) if gene == 0]
team2 = [player_names[i] for i, gene in enumerate(best_individual) if gene == 1]

team1_value = sum((VALUE_WEIGHT * normalized_values[i]) + (FORM_WEIGHT * normalized_grades[i]) for i, gene in enumerate(best_individual) if gene == 0)
team2_value = sum((VALUE_WEIGHT * normalized_values[i]) + (FORM_WEIGHT * normalized_grades[i]) for i, gene in enumerate(best_individual) if gene == 1)

# Function to calculate individual player contribution
def calculate_player_contribution(individual, team_indicator):
    contributions = []
    for i, gene in enumerate(individual):
        if gene == team_indicator:  # Check if player is in the current team
            contribution = (VALUE_WEIGHT * normalized_values[i]) + (FORM_WEIGHT * normalized_grades[i])
            contributions.append((player_names[i], contribution))
    return contributions

# After the genetic algorithm has finished, calculate contributions for both teams
team1_contributions = calculate_player_contribution(best_individual, 0)
team2_contributions = calculate_player_contribution(best_individual, 1)

# Print results
print("\nIndividual Player Contributions for Team 1:")
for player, contribution in team1_contributions:
    print(f"{player}: {contribution:.2f}")

print("\nIndividual Player Contributions for Team 2:")
for player, contribution in team2_contributions:
    print(f"{player}: {contribution:.2f}")

print("\nEvenly Split High-Value Players (88+):")
print("Team 1:", [player_names[i] for i in team1_high_value])
print("Team 2:", [player_names[i] for i in team2_high_value])

print("\nTeam 1:", team1, "- Total Value:", team1_value)
print("Team 2:", team2, "- Total Value:", team2_value)
print("Balance Difference:", abs(team1_value - team2_value))