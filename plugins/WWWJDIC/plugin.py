###
# Copyright (c) 2010, Alex Munroe
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
import supybot.callbacks as callbacks

import urllib
import urllib2
from BeautifulSoup import BeautifulSoup, NavigableString


def urlencode(string):
    """Encodes some string as URL-encoded UTF-8."""
    return urllib.quote(string.encode('utf8'))

class WWWJDIC(callbacks.Plugin):
    """Add the help for "@plugin help WWWJDIC" here
    This should describe *how* to use this plugin."""
    threaded = True

    def jdic(self, irc, msg, args, thing):
        """<thing...>

        Looks up <thing> in the EDICT Japanese dictionary.
        To use roomaji, prefix with @ for hiragana or # for katakana."""

        # Fix encoding.  Sigh.  Stolen from Pokedex.plugin.
        if not isinstance(thing, unicode):
            ascii_thing = thing
            try:
                thing = ascii_thing.decode('utf8')
            except UnicodeDecodeError:
                thing = ascii_thing.decode('latin1')


        # Unnngh this is horrendous.  urllib doesn't understand unicode at all;
        # manually encode as bytes and then urlencode
        url_thing = urllib.quote(thing.encode('utf8'))

        # Hit up wwwjdic
        # 1 = edict; Z = raw results; U = utf8 input; R = exact + common
        res = urllib2.urlopen(
            u"http://www.csse.monash.edu.au/~jwb/cgi-bin/wwwjdic.cgi?1ZUR"
            + url_thing
        )

        # Even the raw results come wrapped in minimal HTML.  This sucks.
        # They're just in this form though:
        # <pre>
        # entry 1
        # entry 2
        # So grab everything from that pre tag, split by lines, and spit it
        # back out.
        soup = BeautifulSoup(res)
        if not soup.pre:
            # Nothing found!  Try again but allow non-P words
            res = urllib2.urlopen(
                u"http://www.csse.monash.edu.au/~jwb/cgi-bin/wwwjdic.cgi?1ZUQ"
                + url_thing
            )
            soup = BeautifulSoup(res)

        if not soup.pre:
            # Still nothing.  Bail.
            reply = u"Hmm, I can't figure out what that means.  " \
                "Perhaps try denshi jisho directly: "

            jisho_url = u"http://jisho.org/words?jap={jap}&eng={eng}&dict=edict"
            if thing[0] in ('@', '#'):
                # Prefixes for roomaji
                reply += jisho_url.format(jap=urlencode(thing[1:]), eng=u'')
            # wtf why is any() overridden
            elif filter(lambda c: ord(c) > 256, thing):
                reply += jisho_url.format(jap=urlencode(thing), eng=u'')
            else:
                reply += jisho_url.format(jap=u'', eng=urlencode(thing))

            self._reply(irc, reply)
            return

        thing_ct = 0
        for entry in soup.pre.string.splitlines():
            entry = entry.strip()
            if entry == '':
                continue

            self._reply(irc, entry)

            # Don't send back more than three; that's probably plenty
            thing_ct += 1
            if thing_ct >= 3:
                break

    jdic = wrap(jdic, [rest('something')])


    def _reply(self, irc, response):
        """Wraps irc.reply() to do some Unicode decoding.

        Also stolen from Pokedex.plugin.
        """
        if isinstance(response, str):
            irc.reply(response)
        else:
            irc.reply(response.encode('utf8'))




Class = WWWJDIC


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
