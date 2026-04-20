import os
from joblib import Memory
from hyperliquid.utils import constants
from hyperliquid.info import Info

# Setup disk caching in the current directory
memory = Memory("./cachedir", verbose=0)
HL_API_URL = os.getenv("HL_API_URL", constants.MAINNET_API_URL)

@memory.cache
def fetch_leaderboard():
    # Initialize Info API with the determined URL
    info = Info(HL_API_URL, skip_ws=True)
    return info.get_leaderboard()

if __name__ == "__main__":
    leaderboard = fetch_leaderboard()
    print(f"Fetched {len(leaderboard)} entries from {HL_API_URL}")