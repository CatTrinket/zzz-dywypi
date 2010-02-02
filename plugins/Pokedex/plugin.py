# encoding: utf8
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

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import pokedex.db
import pokedex.db.tables as tables
import pokedex.lookup

class Pokedex(callbacks.Plugin):
    """Add the help for "@plugin help Pokedex" here
    This should describe *how* to use this plugin."""
    def __init__(self, irc):
        self.__parent = super(Pokedex, self)
        self.__parent.__init__(irc)
        self.db = pokedex.db.connect(self.registryValue('databaseURL'))
        self.indices = pokedex.lookup.open_index(
            directory=conf.supybot.directories.data.dirize('pokedex-index'),
            session=self.db,
        )

    def pokedex(self, irc, msg, args, thing):
        """<thing...>

        Looks up <thing> in the veekun Pokédex."""

        # Similar logic to the site, here.
        results = pokedex.lookup.lookup(thing, session=self.db,
                indices=self.indices)

        # Nothing found
        if len(results) == 0:
            irc.reply("I don't know what that is.")
            return

        # Multiple matches; propose them all
        if len(results) > 1:
            if results[0].exact:
                reply = "Are you looking for"
            else:
                reply = "Did you mean"

            # For exact name matches with multiple results, use type prefixes
            # (item:Metronome).  For anything else, omit them
            use_prefixes = (results[0].exact
                            and '*' not in thing
                            and '?' not in thing)

            result_strings = []
            for result in results:
                result_string = result.name
                if use_prefixes:
                    # Table classes know their singular names
                    prefix = result.object.__singlename__
                    result_string = prefix + ':' + result_string
                result_strings.append(result_string)

            irc.reply("{0}: {1}?".format(reply, '; '.join(result_strings)))
            return

        # If we got here, there's an exact match; hurrah!
        result = results[0]
        if isinstance(result.object, tables.Pokemon):
            irc.reply("""{name}, {type}-type Pokémon.""".format(
                name=result.object.name,
                type='/'.join(_.name for _ in result.object.types),
                )
            )

        elif isinstance(result.object, tables.Move):
            irc.reply("""{name}, {type}-type move.""".format(
                name=result.object.name,
                type=result.object.type.name,
                )
            )

        elif isinstance(result.object, tables.Type):
            irc.reply("""{name}, a type.""".format(
                name=result.object.name,
                )
            )

        elif isinstance(result.object, tables.Item):
            irc.reply("""{name}, an item.""".format(
                name=result.object.name,
                )
            )

        elif isinstance(result.object, tables.Ability):
            irc.reply("""{name}, an ability.""".format(
                name=result.object.name,
                )
            )

        else:
            # This can only happen if lookup.py is upgraded and we are not
            irc.reply("Uhh..  I found that, but I don't know what it is.  :(")

    pokedex = wrap(pokedex, [rest('something')])


Class = Pokedex


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
