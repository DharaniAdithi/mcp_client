
# from dotenv import load_dotenv
# import os
# load_dotenv()
from settings.settings import settings
from tools.tools import generate_quiz,evaluate_answers

app_setting=settings

DB_URI = (
    f"postgresql://{settings.db_username}:"
    f"{settings.db_password}@"
    f"{settings.db_host}:"
    f"{settings.db_port}/"
    f"{settings.db_name_checkpoint}"
)

PYLINT_WORKSPACE="C:/Users/MasanaDuraiM_kfpzclm/Desktop/AI_Platform/langraph-1/temp.py"

# DB_URI = (
#     f"postgresql://{os.getenv('DB_USERNAME')}:"
#     f"{os.getenv('DB_PASSWORD')}@"
#     f"{os.getenv('DB_HOST')}:"
#     f"{os.getenv('DB_PORT')}/"
#     f"checkpoint"
# )

