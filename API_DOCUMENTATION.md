# Football Tracking Backend - API Endpoints Documentation

## Overview

This document describes all the API endpoints available in the football tracking backend system, including functionality for managing teams, players, matches, and goals.

## Default Team

- **Base Camp**: A default team that gets automatically created during database migration/initialization.

## Team Management Endpoints

### Base URL: `/team`

#### 1. Create Team

- **POST** `/team/`
- **Body**: `TeamAdd` schema

```json
{
  "name": "Team Name",
  "description": "Optional team description"
}
```

- **Response**: `TeamResponse` with team details

#### 2. Get All Teams

- **GET** `/team/`
- **Query Parameters**:
  - `skip` (int): Pagination offset
  - `limit` (int): Number of results to return
  - `search` (string): Search teams by name
- **Response**: `TeamListResponse` with list of teams

#### 3. Get Team by ID

- **GET** `/team/{team_id}`
- **Response**: `TeamResponse` with team details and players list

#### 4. Update Team

- **PUT** `/team/{team_id}`
- **Body**: `TeamUpdate` schema
- **Response**: `TeamResponse` with updated team details

#### 5. Add Player to Team

- **POST** `/team/{team_id}/players`
- **Body**: `AddPlayerToTeam` schema

```json
{
  "playerId": 1
}
```

- **Response**: `ConfirmationResponse`

#### 6. Remove Player from Team

- **DELETE** `/team/{team_id}/players/{player_id}`
- **Response**: `ConfirmationResponse`

#### 7. Get Base Camp Team

- **GET** `/team/base-camp`
- **Response**: `TeamResponse` for the default Base Camp team (creates it if doesn't exist)

#### 8. Delete Team

- **DELETE** `/team/{team_id}`
- **Response**: `ConfirmationResponse`

## Player Management Endpoints

### Base URL: `/player`

#### 1. Create Player

- **POST** `/player/`
- **Body**: `PlayerAdd` schema

```json
{
  "name": "Player Name",
  "email": "player@example.com",
  "password": "secure_password",
  "position": "FORWARD",
  "rating": 85
}
```

- **Response**: `PlayerResponse` with player details

#### 2. Get All Players

- **GET** `/player/`
- **Query Parameters**:
  - `skip` (int): Pagination offset
  - `limit` (int): Number of results to return
  - `team_id` (int): Filter by team ID
  - `position` (string): Filter by player position
  - `search` (string): Search players by name
- **Response**: `PlayerListResponse` with list of players

#### 3. Get Player by ID

- **GET** `/player/{player_id}`
- **Response**: `PlayerResponse` with player details

#### 4. Update Player

- **PUT** `/player/{player_id}`
- **Body**: `PlayerUpdate` schema
- **Response**: `PlayerResponse` with updated player details

#### 5. Delete Player

- **DELETE** `/player/{player_id}`
- **Response**: `ConfirmationResponse`

#### 6. Get Free Agents

- **GET** `/player/free-agents/`
- **Query Parameters**:
  - `skip` (int): Pagination offset
  - `limit` (int): Number of results to return
  - `position` (string): Filter by player position
- **Response**: `PlayerListResponse` with players not assigned to any team

## Match Management Endpoints

### Base URL: `/match`

#### 1. Schedule Match

- **POST** `/match/`
- **Body**: `MatchAdd` schema

```json
{
  "team1Id": 1,
  "team2Id": 2,
  "location": "Stadium Arena",
  "timestamp": "2024-12-25T15:00:00"
}
```

- **Response**: `MatchResponse` with match details

#### 2. Get All Matches

- **GET** `/match/`
- **Query Parameters**:
  - `skip` (int): Pagination offset
  - `limit` (int): Number of results to return
  - `team_id` (int): Filter matches by team participation
  - `state` (string): Filter by match state (SCHEDULED, ONGOING, FINISHED)
- **Response**: `MatchListResponse` with list of matches

#### 3. Get Match by ID

- **GET** `/match/{match_id}`
- **Response**: `MatchResponse` with detailed match information including goals

#### 4. Update Match

- **PUT** `/match/{match_id}`
- **Body**: `MatchUpdate` schema

```json
{
  "location": "New Location",
  "timestamp": "2024-12-25T16:00:00",
  "scoreTeam1": 2,
  "scoreTeam2": 1,
  "state": "FINISHED"
}
```

- **Response**: `MatchResponse` with updated match details

#### 5. Update Match Score

- **POST** `/match/{match_id}/score`
- **Body**: `ScoreUpdate` schema

```json
{
  "goals": [
    {
      "playerId": 1,
      "teamId": 1,
      "minute": 45,
      "description": "Header from corner kick"
    }
  ]
}
```

- **Response**: `ConfirmationResponse`
- **Note**: This endpoint requires specifying which players scored for mandatory tracking

#### 6. Finish Match

- **POST** `/match/{match_id}/finish`
- **Response**: `ConfirmationResponse`
- **Description**: Marks the match as finished

#### 7. Delete Match

- **DELETE** `/match/{match_id}`
- **Response**: `ConfirmationResponse`
- **Note**: Can only delete matches that are not finished

#### 8. Get Goals

- **GET** `/match/goals/`
- **Query Parameters**:
  - `skip` (int): Pagination offset
  - `limit` (int): Number of results to return
  - `match_id` (int): Filter goals by match
  - `player_id` (int): Filter goals by player
  - `team_id` (int): Filter goals by team
- **Response**: `GoalListResponse` with list of goals

## Data Models

### Match States

- `SCHEDULED`: Match is scheduled but not started
- `ONGOING`: Match is currently in progress
- `FINISHED`: Match has been completed

### Player Positions

Available player positions (from `PlayerPositions` enum):

- `DEFENDER`
- `MIDFIELDER`
- `FORWARD`
- `GOALKEEPER`

## Key Features

1. **Team Management**: Create, update, delete teams and manage their players
2. **Player Management**: Create players with positions and ratings, manage team assignments
3. **Match Scheduling**: Schedule matches between teams with date/time and location
4. **Score Tracking**: Update match scores with detailed goal information
5. **Goal Tracking**: Mandatory player specification when updating scores for your team
6. **Default Team**: Automatic Base Camp team creation
7. **Free Agent System**: Track players not assigned to any team
8. **Match States**: Track match progression from scheduled to finished

## Usage Examples

### Creating a Match and Updating Score for Base Camp

1. Create the match: `POST /match/` with team IDs
2. During the match, add goals: `POST /match/{match_id}/score` with player details
3. Finish the match: `POST /match/{match_id}/finish`

### Adding a Player to Base Camp Team

1. Get Base Camp team: `GET /team/base-camp`
2. Create or find the player: `POST /player/` or `GET /player/free-agents/`
3. Add player to team: `POST /team/{base_camp_id}/players`

This system provides comprehensive football match tracking with emphasis on detailed goal tracking and team management.
