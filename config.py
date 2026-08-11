import os
from dotenv import load_dotenv

# Load file .env neu co
load_dotenv()

# Telegram Credentials
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")

# Configs cho Inviter (An toan & Chon loc)
DELAY_BETWEEN_INVITES = 35  # Giay nghi giua moi lan add (Nên de >= 30s)
MAX_INVITES_PER_SESSION = 30  # So luong toi da moi lan chay (Tranh spam limit)
CSV_FILE_PATH = "members.csv"
LOG_FILE_PATH = "inviter.log"
