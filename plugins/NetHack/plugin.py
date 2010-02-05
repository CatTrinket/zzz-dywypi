###
# Copyright (c) 2010, Alex "Eevee" Munroe
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.ircmsgs as ircmsgs
import supybot.callbacks as callbacks
import supybot.schedule as schedule

from glob import glob
import os
import os.path
import re

# dnum, used in xlogfile
dungeons = [
    'the Dungeons of Doom',
    'Gehennom',
    'the Gnomish Mines',
    'the Quest',
    'Sokoban',
    'Fort Ludios',
    "Vlad's Tower",
    'the Elemental Planes',
]

# achievements, used by livelog
achievements = [
    'completed the Quest and obtained the Bell of Opening',
    'entered Gehennom',
    'obtained the Candelabrum of Invocation',
    'obtained the Book of the Dead',
    'performed the Invocation',
    'obtained the Amulet of Yendor',
    'reached the Elemental Planes',
    'reached the Astral Plane',
    'ascended to a higher plane of existence',
    "completed Mine's End",
    'completed Sokoban',
    'slew Medusa',
]

def parse_xlog(line):
    line = line.strip()
    data = {}
    for keyval in line.split(':'):
        key, val = keyval.split('=', 1)
        data[key] = val

    ### Extras for us
    # Original and ending gender/alignment are tracked separately
    if data['gender0'] == data['gender']:
        data['gender_delta'] = data['gender']
    else:
        data['gender_delta'] = "%(gender0)s->%(gender)s" % data

    if data['align0'] == data['align']:
        data['align_delta'] = data['align']
    else:
        data['align_delta'] = "%(align0)s->%(align)s" % data

    data['level_desc'] = "%s dlvl %s" % (dungeons[ int(data['deathdnum']) ],
                                         data['deathlev'])
    if data['deathlev'] != data['maxlvl']:
        data['level_desc'] += " (deepest dlvl: %(maxlvl)s)" % data

    # Human-readable time played
    realtime = int(data['realtime'])
    time_secs = realtime % 60;  realtime //= 60
    time_mins = realtime % 60;  realtime //= 60
    time_hrs  = realtime % 24;  realtime //= 24
    time_days = realtime
    # Don't need seconds
    if time_secs >= 30:
        time_mins += 1
    # Construct '0d 0h 5m 12s', then lop off the 0x bits
    data['realtime_pretty'] = re.sub(
        "^(0. )+",
        "",
        "%dd %dh %dm" % (time_days, time_hrs, time_mins)
    )
    return data


def parse_livelog(line):
    line = line.strip()
    data = {}
    for keyval in line.split(':'):
        key, val = keyval.split('=', 1)
        data[key] = val

    return data

def livelog_announcement(livelog):
    # achievement gained
    if 'achieve_diff' in livelog:
        # these are stored as 0xABC
        achieve_diff = int(livelog['achieve_diff'], 16)

        # each item in the achievement list is encoded as that number bit
        for i, achievement in enumerate(achievements):
            if achieve_diff & (1 << i):
                return "{player} just {achievement}, on turn {turns}!".format(
                           achievement=achievement, **livelog)

        # achieve_diff is zero?  nothing changed?  can't happen, but..
        return "{0} just accomplished nothing!".format(player)

    # wishes
    if 'wish' in livelog:
        return "%(player)s just wished for %(wish)s, on turn %(turns)s." % livelog

    # kill a player ghost
    if 'bones_killed' in livelog:
        return "%(player)s just killed the %(bones_monst)s of %(bones_killed)s, " \
               "the former %(bones_rank)s, on turn %(turns)s on dlvl %(dlev)s." % livelog

    # killed a unique monster
    # may result in spam for the three horsemen..
    if 'killed_uniq' in livelog:
        if livelog['killed_uniq'] == 'Medusa':
            # Medusa is already an achievement.  No need to announce twice
            return None
        return "%(player)s has just slain %(killed_uniq)s on turn %(turns)s!" % livelog

    # stole something
    if 'shoplifted' in livelog:
        return "%(player)s just stole %(shoplifted)s zorkmids' worth of merchandise " \
               "from %(shopkeeper)s's %(shop)s, on turn %(turns)s.  Tut tut." % livelog

    # default??
    return "%(player)s just did something-or-other." % livelog

report_template = "{name} ({role} {race} {gender_delta} {align_delta}): " \
                  "{death} on {level_desc}.  {points} points in {turns} turns, " \
                  "wasting {realtime_pretty}.  " \
                  "http://nethack.veekun.com/players/{name}/games/{endtime}"

CONFIG_PLAYGROUND = '/opt/nethack.veekun.com/nethack/var'
CONFIG_USERDATA_FILE = '/opt/nethack.veekun.com/dgldir/userdata'
CONFIG_USERDATA_WEB = 'http://nethack.veekun.com/userdata'
CONFIG_CHANNEL = '#cafe'
class NetHack(callbacks.Plugin):
    """Add the help for "@plugin help NetHack" here
    This should describe *how* to use this plugin."""
    def __init__(self, irc):
        self.__parent = super(NetHack, self)
        self.__parent.__init__(irc)

        self.xlog = open(os.path.join(CONFIG_PLAYGROUND, 'xlogfile'))
        self.livelog = open(os.path.join(CONFIG_PLAYGROUND, 'livelog'))
        self.xlog.seek(0, os.SEEK_END)
        self.livelog.seek(0, os.SEEK_END)

        # Remove the event first, in case this is a reload.  This will fail if
        # this is the first load, so throw it in a try
        try:
            schedule.removePeriodicEvent('nethack-log-ping')
        except:
            pass

        def callback():
            self._checkLogs(irc)
        schedule.addPeriodicEvent(callback, 10, name='nethack-log-ping')

    def _checkLogs(self, irc):
        """Checks the files for new lines and, if there be any, prints them to
        IRC.

        Actual work is all done here.
        """

        # Check xlogfile
        self.xlog.seek(0, os.SEEK_CUR)
        line = self.xlog.readline()
        if line:
            data = parse_xlog(line)
            report = report_template.format(**data)
            msg = ircmsgs.privmsg(CONFIG_CHANNEL, report)
            irc.queueMsg(msg)

        # Check livelog
        self.livelog.seek(0, os.SEEK_CUR)
        line = self.livelog.readline()
        if line:
            data = parse_livelog(line)
            report = livelog_announcement(data)
            if report:
                msg = ircmsgs.privmsg(CONFIG_CHANNEL, report)
                irc.queueMsg(msg)


Class = NetHack


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
