with Session(bind=connection) as session:
    years = (
        session.query(OfficialHolidayYearsModel)
        .filter(
            OfficialHolidayYearsModel.year > target.date.year,
            OfficialHolidayYearsModel.year <= 2100,
        )
        .all()
    )
