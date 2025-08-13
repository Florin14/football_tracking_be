# from pydantic import Field
# from pydantic_settings import BaseSettings
#
#
# class PostgresConfig(BaseSettings):
#     POSTGRESQL_DATABASE: str = Field("template-db", env="POSTGRESQL_DATABASE")
#     POSTGRESQL_HOST: str = Field("localhost", env="POSTGRESQL_HOST")
#     POSTGRESQL_PORT: str = Field("5432", env="POSTGRESQL_PORT")
#     POSTGRESQL_USERNAME: str = Field("template-user", env="POSTGRESQL_USERNAME")
#     POSTGRESQL_PASSWORD: str = Field("template-password", env="POSTGRESQL_PASSWORD")
#
#     def uri(self):
#         return f"postgresql://postgres:1234@localhost:5432/football_tracking_be"
#
#
# postgresConfig = PostgresConfig()
