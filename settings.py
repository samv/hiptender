
import os

BOT_NAME = "Hip Tender"
BOT_NICK = "tender"
BOT_EMAIL = "tender@example.com"
BOT_PASS = "foobarbaz"
BOT_TZ = os.environ.get("TZ", "US/Pacific")
TEAM_ROOM = "Tender Team Room"
STANDUP_ROOM = "Tender Stand-up Room"
STANDUP_ANNOUNCE_COLOR = "green"
STANDUP_WHINGE_COLOR = "red"
WHINGE_INTERVAL = 30

SCHEDULE = "0 11 * * 1-5"

# TODO: knowledge of sprint boundaries and no-standup days
#SPRINT_BOUNDARY = "2013-08-19"
#SPRINT_DAYS = 14
#NO_STANDUP_DAYS = "1,14"
LOOK_BACK_DAYS = 5  # how far back to look for people talking

try:
    from local_settings import *
except ImportError:
    pass
