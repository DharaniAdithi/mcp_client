from sqlalchemy import inspect
from repository.schema.schema import ErrorLogs
from repository.database import Database
 
TABLE_ORDER_CREATION = [
    ErrorLogs.__tablename__,
]

MODEL_CLASSES = {
    ErrorLogs.__tablename__:ErrorLogs,
}

# SQ 1.1 - SQ 1.5 : Inspect database engine to check if ErrorLogs table exists and create it if not found
class Migration:
    def __init__(self):
        self.db = Database()
        self.engine = self.db.engine
        self.inspector = inspect(self.engine)

    def create_tables(self):
        for table_name in TABLE_ORDER_CREATION:
            if not self.inspector.has_table(table_name):
                print("creating table")
                MODEL_CLASSES[table_name].__table__.create(bind=self.engine)
