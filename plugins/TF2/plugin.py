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

from SRCDS import SRCDS

class TF2(callbacks.Plugin):
    """Add the help for "@plugin help TF2" here
    This should describe *how* to use this plugin."""
    threaded = True

    def status(self, irc, msg, args):
        """Checks the status of the TF2 server."""

        ip_port = self.registryValue('IP')
        if ':' in ip_port:
            ip, port = ip_port.split(':', 1)
        else:
            ip = ip_port
            port = 27015

        rcon_password = self.registryValue('rconPassword')

        rcon = SRCDS(ip, port, rcon_password, timeout=2.0)
        server_details = rcon.details()

        players = server_details.get('current_playercount', 0)
        if players == 0:
            template = """Nobody's playing because the server's stuck on {current_map}.  Maybe change to a map that doesn't suck."""
        elif players == 1:
            template = """One lone soul running around {current_map}.  Probably Nimbus."""
        else:
            template = """{current_playercount} dudes on {current_map}.  Stop fucking around on IRC and go join them."""

        irc.reply(template.format(**server_details))

    status = wrap(status)

Class = TF2

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
