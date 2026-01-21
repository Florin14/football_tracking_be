from sqlalchemy import and_, event, exists, insert, literal, select

from modules.ranking.models.ranking_model import RankingModel
from modules.team.models.team_model import TeamModel


@event.listens_for(TeamModel, "after_insert")
def create_ranking_for_team(mapper, connection, target):
    rankings_table = RankingModel.__table__

    exists_conditions = and_(
        rankings_table.c.team_id == target.id,
        rankings_table.c.leagueId == target.leagueId,
    )

    select_stmt = select(
        literal(target.id),
        literal(target.leagueId),
        literal(0),
        literal(0),
        literal(0),
        literal(0),
        literal(0),
        literal(0),
        literal(0),
    ).where(~exists(select(rankings_table.c.id).where(exists_conditions)))

    insert_stmt = insert(rankings_table).from_select(
        [
            rankings_table.c.team_id,
            rankings_table.c.leagueId,
            rankings_table.c.games_played,
            rankings_table.c.games_won,
            rankings_table.c.games_lost,
            rankings_table.c.games_tied,
            rankings_table.c.goals_scored,
            rankings_table.c.goals_conceded,
            rankings_table.c.points,
        ],
        select_stmt,
    )

    connection.execute(insert_stmt)
