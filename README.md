## ABOUT ##

This program is a bot designed for running stand-ups.  Currently it
only handles a single stand-up/team.  It is designed for use with
HipChat.  XMPP support is TODO, in the meantime the bot polls the REST
API.

## INSTALLATION ##

Currently it's not very slick :-)

I'd recommend running it from the checkout:

  virtualenv env && . env/bin/activate
  python setup.py develop
  pip install -r requirements.txt
  pip install -e .

## CONFIGURATION ##

First, copy the configuration files "hipchat.cfg.example" and
"local_settings.py.example" to their proper names:

  cp hipchat.cfg.example hipchat.cfg
  cp local_settings.py.example local_settings.py

Then, edit the files.  The hipchat.cfg needs to contain the API token
that you issued via the API, and it needs to be an admin token.  The
local_settings.py file contains the room names, schedule, and the name
of the bot for tailoring to your needs.

## RUNNING ##

You should be able to run the bot using:

  hiptender

There is currently no command-line parsing.  Patches welcome!

### Using Hiptender ###

Standups are better when held at a regular time, and hiptender only
works with a schedule.  Hiptender will announce to the TEAM_ROOM when
it's time to have the meeting (though a little warning is always nice,
so you should still keep a meeting alarm in your calendar).  Hiptender
will announce a notification if configured and invite people to join
STANDUP_ROOM.

    <Hip Tender> 10:59 AM @all Time for stand-up! Standup is in #standup

Once the standup starts, the last person to speak in either the
standup room or the team room will be called on first.

    <Hip Tender> 11:00 AM @sam your turn

Once you've given your update, use the `next` command to pass to
someone else.

    <Sam Vilain> 11:01 AM yesterday I wrote you, and today I
                          will use you to take over the world.
    <Sam Vilain> 11:02 AM Nothing can stand in my path.
    <Sam Vilain> 11:02 AM @tender next
    <Hip Tender> 11:02 AM @jeb your turn

Once everyone has had their turn, tender will say so and end the
standup.

    <Jeb Fender> 11:02 AM Yesterday I futzed around a bit, today
                          I will try to reel in @sam
    <Jeb Fender> 11:02 AM @tender next
    <Hip Tender> 11:03 AM All done! Stand-up was 3 minute(s),
                          2 second(s)

If you wonder who hasn't yet taken their turns, you can ask with the
`left` command:

    <Sam Vilain> 11:02 AM @tender left
    <Hip Tender> 11:02 AM @sam left to speak: Jeb Fender

During the meeting, if a topic comes up that needs discussion, park it
for later with the `park <topic>` command. Tender will repeat these
topics in the team channel when the meeting is over.

    <Sam Vilain> 11:02 AM @tender park distract @jeb
    <Hip Tender> 11:02 AM @sam parked

    ... later ...

    <Hip Tender> 11:02 AM Parked topics:
                          1. distract @jeb

Everyone should try to stay present during the meeting to help keep it
short.

However if someone had to go AFK and it becomes their turn, you can
also use the `next` command during someone else's turn to come back to
them later:

    <Sam Vilain> 11:02 AM @tender next bob
    <Hip Tender> 11:02 AM @bob your turn

If someone is called on who will not be around to talk, use 'skip':

    <Hip Tender> 11:02 AM @bob your turn
    <Sam Vilain> 11:02 AM @tender skip bob
    <Hip Tender> 11:02 AM All done! Stand-up was 2 minute(s),
                          58 second(s)

## RESPECT ##

Respect goes out to Mark Paschal for writing the original version of
this in Perl.  See https://github.com/markpasc/tender

Sam Vilain
