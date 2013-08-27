#!/usr/bin/env python
#                          -*- coding: utf-8 -*-
# 
#   hiptender - tend daily standup meetings via HipChat
#   Copyright (C) 2013  Sam Vilain <sam@datapad.io>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.


from datetime import date, datetime, timedelta
import logging
import os
import re
import signal
import sys
import time

from crontab import CronTab
from dateutil.parser import parse
import gevent
import hipchat
import hipchat.config
from hipchat.room import Room
from hipchat.user import User
import pytz

import settings

cron = CronTab(tab=settings.SCHEDULE + " standup")
logger = logging.getLogger("hiptender")
state = {}
commands = {
    "help": "say help <command> for help about a command",
    #"standup": "force a stand-up to start now",
    #"start": "begin the stand-up",
    "cancel": "During standup, tell me 'cancel' to abort the stand-up",
    "next": "During standup, tell me 'next' and I'll pick someone to go "
            "next.  The current updater will go last.  You can also tell "
            "me 'next <name>' to tell me <name> should go next.",
    "skip": "During standup, tell me 'skip <name>' and that person will "
            "be taken to have had their turn",
    "park": "During standup, tell me 'park <topic>' and I'll remind you "
            "about <topic> after we're done",
    "left": "During standup, ask me 'left' and I'll tell you who has yet "
            "to be called on",
    #"when": "show next stand-up time",
    #"ignore": "mark a chicken",
    #"heed": "un-mark a chicken / mark a pig",
}


def now():
    return datetime.now(tz=pytz.timezone(settings.BOT_TZ))


def connect_server(cfgfile=None):
    if cfgfile is None:
        cfgfile = os.path.join(
            os.path.dirname(__file__), os.pardir, "hipchat.cfg",
        )
    hipchat.config.init_cfg(cfgfile)
    state["bot_user_id"] = create_user(settings.BOT_NAME)
    state["team_room_id"] = create_room(settings.TEAM_ROOM)
    for standup in cron.find_command("standup"):
        schedule = standup.schedule(date_from=now())
        schedule_standup(schedule)


def schedule_standup(schedule):
    # XXX - allow standups to be skipped on a schedule
    wait = (
        schedule.get_next().replace(tzinfo=pytz.timezone("US/Pacific")) - now()
    ).total_seconds()
    state["standup_room_id"] = create_room(
        settings.STANDUP_ROOM,
        "No standup in progress - quiet please.",
    )
    room_say("next standup in %d seconds" % wait)
    timer = gevent.core.timer(wait, daily_standup, schedule)


def create_user(name):
    found_user = None
    for user in User.list():
        if user.name.lower() == settings.BOT_NAME.lower():
            found_user = user.user_id
    user_settings = dict(
        email=settings.BOT_EMAIL,
        name=settings.BOT_NAME,
        mention_name=settings.BOT_NICK,
        password=settings.BOT_PASS,
        timezone=settings.BOT_TZ,
    )
    if found_user:
        print "found user, updating"
        User.update(user_id=found_user, **user_settings)
        return found_user
    else:
        print "creating bot user %r" % settings.BOT_NAME
        user = User.create(**user_settings)
        return user.user_id


def create_room(room_name, set_topic=None):
    found_room = None
    for room in Room.list():
        if room.name.lower() == room_name.lower():
            found_room = room.room_id

    if found_room:
        if set_topic:
            print "updating room topic to %r" % set_topic
            Room.topic(
                room_id=found_room,
                topic=set_topic,
                **{"from": settings.BOT_NAME}
            )
        return found_room
    else:
        print "creating new room %s" % room_name
        room = Room.create(
            name=room_name,
            owner_user_id=state["bot_user_id"],
            topic=set_topic or "(go team!)",
        )
        return room.room_id


def recent_users():
    today = date.today()
    start = today - timedelta(days=settings.LOOK_BACK_DAYS)
    users = dict((u.user_id, u) for u in User.list())
    seen = set()
    day = start
    user_order = list()

    while day <= today:
        kwargs = dict(
            date=day.strftime("%Y-%m-%d"),
            timezone=settings.BOT_TZ,
        )
        try:
            day_talk = (
                Room.history(room_id=state["team_room_id"], **kwargs) +
                Room.history(room_id=state["standup_room_id"], **kwargs)
            )
            for message in day_talk:
                if message.sort != "message":
                    continue
                from_info = getattr(message, "from")
                user_id = from_info["user_id"]
                if user_id in (u"api", state["bot_user_id"]):
                    continue
                if user_id not in seen:
                    logger.info("Added %s to the standup" % from_info["name"])
                    print "Added %s to the standup" % from_info["name"]
                    seen.add(user_id)
                if user_id in user_order:
                    del user_order[user_order.index(user_id)]
                user_order.append(user_id)
        except Exception, e:
            logger.warning(
                "error fetching history for %s: %r" % (
                    day.strftime("%Y-%m-%d"), e,
                )
            )
        day += timedelta(days=1)

    user_order.reverse()
    return users, user_order


def daily_standup(schedule):
    state["standup_start"] = state["last_checked"] = now()
    state["standup_room_id"] = create_room(
        settings.STANDUP_ROOM,
        "Standup in progress - wait for your turn",
    )
    room_say(
        message=("@sam Time for stand-up!  Standup is in #%s" %
                 settings.STANDUP_ROOM),
        color=settings.STANDUP_ANNOUNCE_COLOR,
        room="team",
    )
    state["users"], state["todo"] = recent_users()
    state["nicks"] = dict(
        (user.mention_name, user.user_id) for user in state["users"].values()
    )
    state["schedule"] = schedule
    state["parked_topics"] = list()
    do_next()

    schedule_loop()


def schedule_loop():
    gevent.core.timer(5, standup_loop)


def standup_loop():
    recent_msgs = Room.history(
        room_id=state["standup_room_id"],
        timezone=settings.BOT_TZ,
        date="recent",
    )
    for msg in recent_msgs:
        msg_date = parse(msg.date)
        if msg_date <= state["last_checked"]:
            continue
        from_info = getattr(msg, "from")
        if from_info["user_id"] in state["users"]:
            process_message(msg)

    state["last_checked"] = msg_date
    if len(state["todo"]):
        schedule_loop()
    else:
        standup_done()


def room_say(message, fmt="text", notify=1, color="yellow", room="standup"):
    print "Saying in %s room: %s" % (room, message)
    Room.message(
        room_id=state["%s_room_id" % room],
        message=message,
        message_format=fmt,
        notify=notify,
        color=color,
        **{"from": settings.BOT_NAME}
    )


def handle_help(arg, user):
    prefix = "@{who} ".format(who=user.mention_name)
    if len(arg):
        if arg not in commands:
            room_say(prefix + ("%r is not a command" % arg))
        else:
            room_say(prefix + commands[arg])
    else:
        room_say(
            prefix + "say '@{me} <command> <args>' to control me.  "
            "<command> may be one of: ".format(me=settings.BOT_NICK) +
            ", ".join(sorted(commands.keys()))
        )


def handle_left(arg, user):
    room_say(
        "@{who} left to speak: " + ", ".join(
            list(state["users"][x].name for x in state["todo"]),
        ).format(who=user.mention_name)
    )


def do_next():
    if len(state["todo"]):
        next_user_id = state["todo"][0]
        next_user = state["users"][next_user_id]
        logger.info(
            "It's now %s's turn (@%s)" % (
                next_user.name, next_user.mention_name,
            )
        )
        room_say(
            "@{who} your turn".format(
                who=next_user.mention_name,
            )
        )


def nick_to_user_id(arg):
    m = re.match(r'\s*@?(\w+)', arg)
    if not m or m.group(1) not in state["nicks"]:
        room_say(
            prefix + "bad argument '%s'" % arg,
            color=settings.STANDUP_WHINGE_COLOR,
        )
        return None
    return state["nicks"][m.group(1)]


def handle_next(arg, user):
    prefix = "@{who} ".format(who=user.mention_name)
    if len(arg):
        next_user_id = nick_to_user_id(arg)
        if next_user_id is None:
            return
        if next_user_id not in state["todo"]:
            room_say(
                "%s%s is not on my list to speak." % (
                    prefix, next_user_id.name,
                ),
                color=settings.STANDUP_WHINGE_COLOR,
            )
            return
        del state["todo"][state["todo"].index(next_user_id)]
        state["todo"][:0] = (next_user_id,)
    else:
        state["todo"][:1] = ()

    do_next()


def handle_skip(arg, user):
    prefix = "@{who} ".format(who=user.mention_name)
    if not len(arg):
        room_say(
            prefix + "skip whom?",
            color=settings.STANDUP_WHINGE_COLOR,
        )
        return
    skip_user_id = nick_to_user_id(arg)
    if skip_user_id is None:
        return
    skip_user = state["users"][skip_user_id]

    if skip_user_id in state["todo"]:
        due_index = state["todo"].index(skip_user_id)
        del state["todo"][due_index]
        if due_index == 0:
            do_next()
        else:
            room_say(
                prefix + "skipping @{them}".format(
                    them=skip_user.mention_name,
                )
            )


def handle_park(arg, user):
    prefix = "@{who} ".format(who=user.mention_name)
    if not len(arg):
        room_say(
            prefix + "park what?",
            color=settings.STANDUP_WHINGE_COLOR,
        )
    else:
        state["parked_topics"].append(arg)
        room_say(prefix + "parked")


def handle_cancel(arg, user):
    room_say("the stand-up is CANCELED")
    schedule_standup(state["schedule"])


def process_message(message):
    if message.sort != "message":
        return

    text = message.message
    from_info = getattr(message, "from")
    user_id = from_info["user_id"]
    user = state["users"][user_id]

    print "message from @%s: %s" % (user.mention_name, text)
    
    command_prefix = "@" + settings.BOT_NICK
    if text.startswith(command_prefix):
        command = text[len(command_prefix)+1:]
        m = re.match(r"^\s*(\w+)(?:\s+(\S.*?))?\s*$", command)
        if not m or m.group(1).lower() not in commands:
            room_say(
                "@{who} what?  say 'help' for instructions.".format(
                    who=user.mention_name,
                ),
                color=settings.STANDUP_WHINGE_COLOR,
            )
            return
        command_func = m.group(1).lower()
        command_args = m.group(2) or ""
        print "command from @%s: %s (%s)" % (
            user.mention_name, command_func, command_args,
        )
        globals()["handle_%s" % command_func](command_args, user)

    elif user_id != state["todo"][0]:
        # whinge if people speak out of turn
        if "last_whinged" not in state["last_whinged"] or (
            now() - state["last_whinged"]
        ) > timedelta(seconds=settings.WHINGE_INTERVAL):
            room_say(
                "@{who} hey!  It's not your turn!  Try '@{me} skip {them}'"
                .format(
                    who=user.mention_name,
                    me=settings.BOT_NICK,
                    them=state["users"][state["todo"]].mention_name,
                ),
                color=settings.STANDUP_WHINGE_COLOR,
            )
            state["last_whinged"] = now()


def standup_done():
    elapsed = now() - state["standup_start"]
    room_say(
        "All done!  Stand-up was {days}{minutes}{seconds}".format(
            days="" if elapsed.days == 0 else "%d day(s), " % elapsed.days,
            minutes="" if elapsed.seconds < 60 else "%d minute(s), " % (
                elapsed.seconds / 60
            ),
            seconds="%d second(s)" % (elapsed.seconds % 60),
        )
    )
    if len(state["parked_topics"]):
        from cgi import escape
        room_say(
            "<p>Parked topics:<br><ol>" + "".join(
                "<li>%s</li>" % escape(x) for x in state["parked_topics"]
            ) + "</ol>",
            fmt="html",
            room="team",
        )
    schedule_standup(state["schedule"])


terminate = False


def shutdown():
    print "Caught signal, terminating"
    logger.info("Caught signal, terminating")
    global terminate
    terminate = True


def main():
    # XXX - parse command-line
    gevent.signal(signal.SIGTERM, shutdown)
    greenlet = gevent.spawn(connect_server)
    gevent.joinall([greenlet])
    global terminate
    while not terminate:
        try:
            gevent.sleep(3600)
        except KeyboardInterrupt:
            print "Caught interrupt, what should I do?"
            terminate = True
            import gc
            from greenlet import greenlet
            for ob in gc.get_objects():
                if isinstance(ob, greenlet):
                    print "Canceling %r" % ob
                    ob.throw()
            #print "GEvent shutdown"
            #gevent.shutdown()
            print "sys.exit()"
            sys.exit()


if __name__ == "__main__":
    print """hiptender 0.01  Copyright (C) 2013  Sam Vilain
    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under certain conditions; see the source for details."""
    ch = logging.StreamHandler(sys.__stderr__)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    main()
