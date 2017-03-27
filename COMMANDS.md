# Commands

At the heart of the CSL framework are **commands**, which let league admins
(or anyone with edit access to the league workbook) configure the league's
operation. Almost all of them are optional and come with default values (i.e.,
you don't have to worry about them unless you want to use them) but give you
the ability to do a lot of interesting things with your league cluster.

You should enter commands from a worksheet titled "Settings" (any worksheet
titled "Settings" will be assumed to be the commands sheet.) The first row
should be the header, with the columns titled "Command", "League", and "Args".

If you're not sure how to set up the commands sheet, just share your workbook
with cslbot (see the Setup instructions) and it will create it for you the next
time it encounters your workbook. Then you can use it to enter commands.

## Structure

Each command has 3 components:
(Note: for the sake of differentiating keyword strings, they have been put in
double quotes; don't put double quotes in the strings you actually enter into
the sheet.)

* **Command**: the command type (e.g., "LEAGUES", "THREAD", "RATING SYSTEM");
  this has to be in all caps to reduce the risk of accidental commands
* **League**: the league to which the command applies. The keyword "ALL"
  would cause a command to apply to all leagues within the cluster. General
  commands (i.e., those where the League is specified as "ALL") will be
  overriden if a league-specific command (i.e., a command where the league is
  specified using its name, like "1v1" if you have created a league called
  1v1.)
* **Args**: the arguments to pass to a command; either a single value or a
  comma-separated list (depending on the command type.)

## Commands List

This is a comprehensive list of all commands supported by the CSL framework,
their argument types. Outside the "LEAGUES", "ADMIN", and "THREAD" commands,
any command can specify any league it applies to, including all leagues using
the "ALL" keyword.

### Required Commands

### Basic Setup

**THREAD**: The ID or URL (discouraged) of the Warlight forum thread tied to the league.

*This command does not require a League to be specified*

*Sample Args*: "6911420", "https://www.warlight.net/Forum/6911420-fizzer-sux"

For abuse-prevention purposes, the top post in the thread *must* validate its
connection to the sheet using the "!validate\_league" command in the format
"!validate\_league {{sheet ID}}" where the sheet ID can be extracted from the
URL of the worksheet. For example, in:

https://docs.google.com/spreadsheets/d/THISISWHERETHESHEETIDSHOULDBE/edit#gid=THISISATABID

the sheet ID value would be "THISISWHERETHESHEETIDSHOULDBE" (without the
quotes, of course) and the validation command would look like:

"!validate\_league THISISWHERETHESHEETIDSHOULDBE"

**LEAGUES**: A comma-separated list of all the leagues tied to this sheet.

*This command does not require a League to be specified*

*Sample Args*: "1v1", "PR,ELIM,CRAZY", "a,whole,bunch,of,leagues"

As part of the league cluster, all of these leagues will share the same thread
and workbook (but not necessarily the same configuration- i.e., you can have an
Elo-rated elimination ladder and a TrueSkill-rated seasonal ladder with
completely different settings running from the same workbook). Each league will
be identified by a unique name; these are the names you can specify under
"LEAGUE" title for other commands.

Each league will have its own "Game Data", "Team Data", and "Template Data"
worksheets- named after the league. For a league named "1v1", the game data
sheet would be named "Game Data (1v1)".

### Optional Commands

### Admin Specification

**ADMIN**: The Warlight ID of the owner of this league cluster.

*This command does not require a League to be specified*

*Sample Args*: "3022124041"

Only one admin can be specified for the league. Ideally should be same as the owner of the workbook where the league data is
stored. Admin is the highest level of authorization for thread
orders, so make sure this actually goes to whoever runs the league cluster.

### League Setup

**MODS**: A comma-separated list of Warlight IDs of league mods.

*Sample Args*: "3022124041", "1,2,3,4"

*Default*: No mods

You can specify as many mods as possible. Mods have a higher level of
authorization for thread orders- they're able to create teams that don't
include them, confirm team membership on behalf of other players, set the limit
for teams they don't belong to, and toggle the activity status of templates.

**AUTOFORMAT**: Whether to automatically format the league sheets.

*Possible Args*: "TRUE", "FALSE"

*Default*: True

This is not a setting worth worrying about unless you really know what you're
doing. Basically, if a required label (like 'ID' for the teams sheet) is
missing in a league's games, templates, or teams sheet, setting AUTOFORMAT to
true will let you not worry about it because the bot will just fix any
inconsistencies it finds. Set this to false only if you're 100% sure you've got
the sheets formatted exactly the way you want and are worried about bot edits-
that way, if the bot thinks the sheets are not formatted properly, it will
raise and log an error instead of messing around with the header and you'll be
able to try and fix things yourself.

### Basic League Design

### Game Setting Configurations

**MESSAGE**: This is the message that goes out with every game created
for the league.

*Sample Args*: "Hi this is my league kthxbai"

*Default*:
"""
This is a game for the {{\_LEAGUE\_NAME}} league, part of {{CLUSTER NAME}}.

To view information about the league, head to {{URL}}.
To change your limit, add/confirm a team, etc.,
head to the league thread at {{\_LEAGUE\_THREAD}}.

Vetos so far: {{\_VETOS}}; Max: {{VETO LIMIT}}

{{\_GAME\_SIDES}}

This league is run using the CSL framework,
an open-source project maintained by knyte.

To view the source code, head to:
https://github.com/knyte/cslbot

If you never signed up for this game or suspect abuse,
message knyte - tinyurl.com/mail-knyte
"""

You'll notice that there are some special tags that can be used in messages.
Here's a list of all of them, with some basic descriptions:

* **\_LEAGUE\_NAME**: The name of the league (as declared in **LEAGUES**)
* **CLUSTER NAME**: The name for the cluster (as declared using **CLUSTER
  NAME**)
* **\_LEAGUE\_THREAD**: The URL for the league thread
* **\_VETOS**: Vetos so far for this game
* **VETO LIMIT**: This league's veto limit (as declared using **VETO LIMIT**)
* **\_GAME_SIDES**: The name, rank, and rating for each team on each side of
  the game

**CLUSTER NAME**: The name of the league cluster to which this league belongs.

*Sample Args*: "Infinity Premier League", "Hydra Clan Ladders"

*Default*: Same as the league name

You can have multiple clusters within the same workbook (although they'll still
share the same thread and workbook). For example, if some of the leagues in
your workbook are round-robins and the rest are seasonal, you can use the
CLUSTER NAME command (for each league in the workbook) to specify which belongs
to which cluster.

**SHORT NAME**: A name for the league to be used in game titles.

*Sample Args*: "IPL", "MDL", "1v1 Ladder", "Ligue One"

*Default* Same as the cluster name

This comes at the start of the titles for any games created in this league. For
example, all games in a hypothetical league with the short name "IPL" will have
their titles start with "IPL | ".

**URL**: A URL where players can head to if they want to check out the league.

*Sample Args*: 'http://tinyurl.com/fake-league'

*Default*: URL of the league workbook

This is where players should be able to head for league stats, etc., ideally
just a short URL to the league workbook. It's recommended to use a URL
shortener for this since users might have to remember and/or type out the URL.

### League Mechanics

### Activity Controls

**ACTIVE**: Whether to create new games for this league.

*Possible Args*: "TRUE", "FALSE"

*Default*: True

You can set this manually or using a formula (if you have special rules). Also
see **ALLOW JOINING** if you want to just control the addition of new teams.
This is overriden by **LEAGUE START** and **LEAGUE END** if they are more
restrictive.

**LEAGUE START**: The start time for the league.

*Sample Args*: "2015-04-20 01:02:03", "1994-03-09 10:12:40"

*Default*: no restriction

No games will be created before the LEAGUE START. The date supplied must be in
a "YYYY-mm-dd HH:MM:SS" format with zero-padding. Even after the league start,
if the league is not **ACTIVE**, games will not be created. This is in the
timezone of the machine running the cslbot instance (US Eastern).

**LEAGUE END**: The end time for the league.

*Sample Args*: "2015-04-02 01:02:06", "1995-03-09 10:12:40"

*Default*: no restriction

See **LEAGUE START** for important information about the time format. Keep in
mind that you can have a LEAGUE END defined without explicitly defining the
LEAGUE START (and vice versa).

**MIN TEAM COUNT**: The minimum number of teams before games are created.

*Sample Args*: "0", "10", "50"

*Default*: enough teams to create 1 game

If you want to avoid starting the league until it's big enough to have decent
matchups, you can set this to a specific value. If you start the league too
early, you can have teams end up with opponents out of their league (because
there aren't enough opponents in their league) or have the league take a long
pause because all the teams have already played one another recently enough
that your **REMATCH HORIZON** gets in the way of creating new games.

Keep in mind that, for abuse-prevention reasons, the league won't even start
until at least 5 unique people have commented on the league thread.

**MIN ACTIVE TEMPLATES**: The minimum number of active templates.

*Sample Args*: "0", "10", "15"

*Default*: 1

Mods will not be able to deactivate any more templates once this limit is
reached (they can reactivate templates to make up for it, though). On top of
that, the league will not run if there are not enough active templates.

### League Definition

**TEAM SIZE**: The number of players per team. (This must be an integer.)

*Sample Args*: any integer value 

*Default*: 1

If you have players sign up in groups of 2 in a 2v2 league, this would be 2.
If you have players sign up in groups of 1 in a 2v2 league (and automatically
pair them), this would be 1 since the basic unit of the league is a 1-member
team.

**TEAMS PER SIDE**: The number of teams per side. (This must be an integer.)

*Sample Args*: any integer value

*Default*: 1

Each game in the league is basically XvXv...XvX where X is a number of players.
Here, you're specifying the number of *teams* in each of those X's- so if you
have a 2v2 league where the team size is 2, this would be 1. If you have a 8v8
league where people join and compete in teams of 4, this would be 2.

Or in other words, this is the number of players on each side of a game divided
by the number of players on each side.

**GAME SIZE**: The number of sides to a game. (This must be an integer.)

*Sample Args*: any integer value

*Default*: 2

In an XvXv....XvX game, this is the number of v's + 1. So in a 2v2 league, this
would be 2. In a 5v5v5 league, this would be 3- there's 3 sides of 5 players
each competing in every single game.

**RATING SYSTEM**: The rating system used by the league.

*Possible Args*: "ELO", "GLICKO", "TRUESKILL", "WINCOUNT", "WINRATE"

*Deault*: Elo

If you switch rating systems after a league has already started, you will have
to manually update the rating for each team to match the format- so it's
strongly discouraged to do so. On top of that, your ratings will be less
accurate since league pairings and rating updates are based on prior ratings.

Here's quick descriptions of each rating system you can use:

* **ELO**: The classic Elo system. Simple, easy to configure and debug.

* **GLICKO**: The Glicko-2 system, where each rating is stored as both a rating
  and a rating deviation (with a 95% chance the *actual* rating of a given team
  is within the range [rating - 2 * rating deviation, rating + 2 * rating
  deviation]).

* **TRUESKILL**: The TrueSkill system developed by Microsoft and once used on
  Xbox Live. Ratings are stored in a way similar to Glicko, but TrueSkill is
  very flexible with relation to game structure. Strongly recommended if your
  league has more than 2 sides per game (Game Size) or teams per side.

* **WINCOUNT**: Each team is simply rated based on the number of games they
  have won. Useful for round-robins.

* **WINRATE**: Each team is rated based on the *portion* of games they have
  won so far. Also useful for round-robins. Keep in mind this does not take
  into account the skill of each team's opponents and so there's a tendency
  to push teams closer to .500 or to 1.000 (depending on the **PREFER SKEWED
  MATCHUPS** setting). Win rates are stored on a scale of 0 to 1000.

**MIN GAMES TO RANK**: Minimum number of completed games before a team can be
ranked.

*Sample Args*: "1", "5", "10"

*Default*: 0 (no minimum)

Teams that have not yet finished this number of games (by win, loss, or
excessive vetos) will not be ranked. This also helps you control the impact of
other settings like **MAX RANK** to make sure that a flood of incoming new
teams will not artificially push down existing teams and reduce the impact of
random early fluctuations in your rankings.

**MIN LIMIT TO RANK**: Minimum number of games a team must be willing to
participate in simultaneously in order to get/remain ranked.

*Sample Args*: "0", "1", "5"

*Default*: 1

This is to basically keep inactive teams (or teams below a certain activity
threshold) from affecting your league rankings.

**EXPIRY THRESHOLD**: Number of days until a game is considered abandoned.

*Sample Args*: "1", "2", "5"

*Default*: 3

If a game is in the lobby for a long-enough while, it will be considered
abandoned (or vetoed if you enable that feature) and all teams that have yet to
accept the game will be penalized (if you enable that feature).

**ALLOW REMOVAL**: Whether to allow teams to remove themselves (and potentially
start over with new default ratings).

*Possible Args*: "TRUE", "FALSE"

*Default*: False

If this is set to true, teams can simply remove themselves and start over with
a default rating. The other side effect is that any opponents they have in
ongoing games will not have their ratings adjusted as if they had beaten a team
with a default rating (as this team's data will be removed). This is rather
dangerous to play around with and opens the door to abuse and some messes, but
it also gives teams a second chance to start from scratch if their skill has
changed so significantly that the ladder rating system hasn't kept up. Even if
you disable this, teams will be able to set their limit to 0 and thereby
discontinue participation without deleting all their data/history.

**REMOVE DECLINES**: Whether to remove Declined teams from the league (by
setting their Limit to 0).

*Possible Args*: "TRUE", "FALSE"

*Default*: True

If you want players to be able to exit the league just by declining a game (to
avoid the risk of players tanking their team's rating when they're simply trying to
quit the league), set this to be true.

**COUNT DECLINES AS VETOS**: Whether to consider declines as vetos (as well as
losses).

*Possible Args*: "TRUE", "FALSE"

*Default*: False

If you set this to be true, all declines will be considered as the team vetoing
the game's template and as such their odds of playing on the same template
again will be reduced. Declines will still count as losses, though.

**REMATCH HORIZON**: Number of (most recent) games from which opponents/allies
will be excluded from new matches.

*Possible Args*: "1", "10", "15", "ALL"

*Default*: 0 (no restriction)

You can use this to avoid rematches with recently-matched teams. Keep in mind
that this is a number of *games* not teams, so if your league has a
particularly large number of teams per game you'd want to set this to a smaller
number. On top of that, this doesn't prevent rematches against the same player
if they are on multiple teams (of which at least one has not yet been faced). 
But you can use this to keep the same teams from matching up against each other
multiple times in a row. There are already safeguards in place to keep a single
team from matching up with the same allies/opponents during multiple games
created in the same batch.

If you set this to ALL, teams will never be matched with/against any team
they've played with before- so you can set up round robins this way.

### Participation Control

Requirements are checked every time a league is run, so players can't evade bans by
simply temporarily changing their location/clan/etc.

### Player/Clan/Location Restrictions

**BANNED PLAYERS**: A comma-separated list of Warlight IDs of banned players.

*Sample Args*: "3022124041", "1,2,3,4", "ALL"

*Default*: No one banned, although cslbot will not work if a player in the
league has blacklisted the account providing cslbot's Warlight credentials

You can ban players using their Warlight IDs- if they're found to be
somehow cheating, for example. You can set this to "ALL" if you want to ban
players by default (BANNED PLAYERS is overriden by **ALLOWED PLAYERS** so if
you allow someone explicitly they'll get in even if you use the "ALL" keyword
here- or even if you explicitly ban them).

**ALLOWED PLAYERS**: A comma-separated list of Warlight IDs of explicitly allowed players.

*Sample Args*: "3022124041", "1,2,3,4"

*Default*: No one

You can also explicitly allow players using their Warlight IDs. If you're
running an exclusive league, for example, that's not based on an automatically
discernible feature, you can simply just allow the players to join your league.

**REQUIRE CLAN**: Whether to require all players to belong to a clan.

*Possible Args*: "TRUE", "FALSE"

Setting **BANNED CLANS** to "ALL" will also ban any unclanned players unless
this is explicitly set to false.

**BANNED CLANS**: A comma-separated list of Warlight clan IDs of banned clans.

*Sample Args*: "12", "160,161", "ALL"

*Default*: No clans banned

You can ban clans using their Warlight clan IDs (which you should be able to
find from their clan page URLs). You can set this to "ALL" if you want to ban
all clans by default (so you can explicitly allow certain clans and only those
clans using the **ALLOWED CLANS** commands). Using the "ALL" keyword will also
ban any unclanned players unless you explicitly set **REQUIRE CLAN** to false. 

**ALLOWED CLANS**: A comma-separated list of Warlight clan IDs of explicitly
allowed clans.

*Sample Args*: "10,20,30", "5"

*Default*: No clans

If you want your league to only be open to players belonging to certain clans,
you can set that using their clan IDs. If you want to also allow unclanned
players but have set **BANNED CLANS** to "ALL", you should also toggle
**REQUIRE CLAN** to be false (otherwise it'll be assumed you're only allowing
players that belong to a certain clan).

**BANNED LOCATIONS**: A comma-separated list of banned location names.

*Sample Args*: "Morocco", "France,Germany,Denmark", "Pennsylvania,Texas", "ALL"

*Default*: No locations banned

If you want your league to only be open to players from a certain location or
group of locations, you can specify that here. This is useful if you want to
run a language/region-specific league, for example; you could use this to only
allow players from Germany for a German-speaking league and then **ALLOWED
PLAYERS** to make manual exceptions to cover players who are unfortunate enough
to reside outside Schland. You should probably check the country values in
player profiles to see how Warlight formats the name of a particular region you
want to allow or ban. **Since Warlight sometimes specifies US states**, the
states and the United States are treated as separate values in here. If you
want to ban *all* the American states, you can simply ban the United States. if
you want to ban some American states, you can either ban them individually or
ban the United States as a whole and use **ALLOWED LOCATIONS** to allow the
ones you want to allow. But if you allow the United States as a whole
(explicitly, using ALLOWED LOCATIONS) you will not be able to ban any American
states. The process works similarly for any other locations provided by
Warlight with multiple degrees of resolution.

In simple terms, any location with multiple degrees of resolution will have its
status determined by thus:

- If any degree of resolution is explicitly allowed, the player will be
  allowed.
- If no degree of resolution is explicitly allowed but no degree is explicitly
  banned either, the player will be allowed.
- If some degree of resolution is explicitly banned and no other degree of
  resolution (higher or lower) is explicitly allowed, the player will be
  disallowed.

**ALLOWED LOCATIONS**

*Sample Args*: "Argentina,Nicaragua,Texas", "United States,United Kingdom"

*Default*: No locations

Any location explicitly allowed (at any degree of resolution, if there are
multiple- e.g., a player from Texas will get in through this if either the US or Texas is
explicitly allowed) to participate should be in this comma-separated list.

See the discussion under **BANNED LOCATIONS** for more details, especially if
you're planning on dealing with American states.

### Player Join Prerequisites

These can be explicitly overriden for players using the **ALLOWED PLAYERS**
command. So if a player is ineligible to participate based on prereqs but you
still want them to allow them to participate without changing the rules for
everyone else, you can do so.

**MAX BOOT RATE**: Maximum boot rate (as a percentage on a 0-100 scale).

*Sample Args*: "5.0", "8", "90"

*Default*: 100.0 (no maximum)

If a player's boot rate is strictly higher than the MAX BOOT RATE, they will
not be allowed to participate in the league.

**MIN LEVEL**: Minimum level on Warlight (integer).

*Sample Args*: "10", "50"

*Default*: 0 (no minimum)

If a player's level is strictly beow the MIN LEVEL, they will not be allowed to
participate.

**MEMBERS ONLY**: Whether to restrict the league to just Warlight Members.

*Possible Args*: "TRUE", "FALSE"

*Default*: False

If this is set to true, only Warlight Members will be allowed to participate.
So if you want to pick up the slack for Fizzer when it comes to Warlight Member
benefits, you can enable this.

**MIN POINTS**: Minimum points over the last 30 days (integer).

*Sample Args*: "0", "1000", "90000"

*Default*: 0 (no minimum)

You can use this to weed out less-active players, although **MAX LAST SEEN**
is likely better for that.

**MIN AGE**: Minimum number of days since joining Warlight (integer).

*Sample Args*: "0", "10", "30"

*Default*: 0 (no minimum)

You can use this to weed out new accounts, especially if you have a troll
problem.

**MIN MEMBER AGE**: Minimum number of days since Warlight Membership (integer).

*Sample Args*: "0", "10", "30"

*Default*: 0 (no minimum)

Setting this to a non-zero value will also make the league Members-only,
regardless of the value of **MEMBERS ONLY**.

**MAX RT SPEED**: Maximum number of *minutes* per average turn in RT games.

*Sample Args*: "5", "10", "30"

*Default*: no maximum

If you want to weed out slowpokes in RT games, you can use this.

**MAX MD SPEED**: Maximum number of *hours* per average turn in MD games.

*Sample Args*: "1", "5", "30"

*Default*: no maximum

If you want to weed out slowpokes in MD games, you can use this.

**MIN ONGOING GAMES**: Minimum number of ongoing (multi-day) games.

*Sample Args*: "0", "5", "30"

*Default*: 0 (no minimum)

Just another way to set a minimum activity threshold.

**MAX ONGOING GAMES**: Maximum number of ongoing (multi-day) games.

*Sample Args*: "0", "5", "30"

*Default* no maximum

You can set this to a specific value if you want to avoid players who are
possibly overstretched.

**MIN RT PERCENT**: Minimum % of played games that were real-time

*Sample Args*: "0", "10", "51.43"

*Default*: 0 (no minimum)

Players are allowed so long as RT games constitute at least this percent of
their overall gameplay.

**MAX RT PERCENT**: Maximum % of played games that were real-time

*Sample Args*: "10", "20.3", "100"

*Default*: 100 (no maximum)

If you want to weed out players that mostly play RT games.

**MAX LAST SEEN**: Maximum number of days since the player was last online.

*Sample Args*: "3", "5", "10"

*Default*: no maximum

Since prerequisites are checked every time a league is run and before games are
created, you can automatically weed out inactive players' teams before even
creating games with those players. Be careful about setting this limit too low,
though, because you could accidentally deactivate teams where the players were
active or just temporarily gone.

**MIN 1v1 PERCENT**: Minimum win rate in ranked 1v1 games.

*Sample Args*: "10", "50", "66.6"

*Default*: 0 (no minimum)

This is across ranked games only.

**MIN 2v2 PERCENT**: Minimum win rate in ranked 2v2 games.

*Sample Args*: "10", "50", "66.6"

*Default*: 0 (no minimum)

This is across ranked games only.

**MIN 3v3 PERCENT**: Minimum win rate in ranked 3v3 games.

*Sample Args*: "10", "50", "66.6"

*Default*: 0 (no minimum)

This is across ranked games only.

**MIN RANKED GAMES**: Minimum number of ranked games to participate.

*Sample Args*: "10", "50", "200"

*Default*: 0 (no minimum)

You can use this to weed out weak players and trolls creating accounts to abuse
or spam your league.

**MIN PLAYED GAMES**: Minimum number of finished games to participate.

*Sample Args*: "10", "50", "200"

*Default*: 0 (no minimum)

This is across all games, not just ranked games- so Practice diplos/etc. are
counted. You can still probably use this to weed out trolls but it's likely
less effective than **MIN RANKED GAMES** at weeding out inexperienced players
in strategic games.

**MIN ACHIEVEMENT RATE**: Minimum achievement rate to participate.

*Sample Args*: "10", "50", "60"

*Default*: 0 (no minimum)

This is from the top right of the player profile- what % of Warlight
achievements they've finished. Setting this to a reasonable value can also
deter trolls or newbies, but this probably should not be your first resort for
that purpose.

### Seasonal Ladders

**ALLOW JOINING**: Whether to allow new teams to join.

*Possible Args*: "TRUE", "FALSE"

*Default*: True

You can use this to manually whether players are able to join your league. Or
if you have some fancier rules, you could use a Google Sheets formula to
set this value based on those rules. This is overriden by **JOIN PERIOD START**
and **JOIN PERIOD END** if a request is processed outside the join period, but
can conversely override those commands if a request is processed within the
join period but ALLOW JOINING is set to false.

**JOIN PERIOD START**: The time at which join requests can be accepted.

*Sample Args*: "2015-04-12 10:00:00", "2017-01-01 00:00:00"

*Default*: no restriction

This has to follow a particular time format- "YYYY-mm-dd HH:MM:SS" (with
zero-padding). Keep in mind this is based on when an add\_team command is
*processed*, not when it's made, and that it's also dependent on the timezone
of the machine on which cslbot runs (US Eastern). When in doubt, leave some
room or just use **ALLOW JOINING** and a formula.

**JOIN PERIOD END**: The time at which join requests are no longer accepted.

*Sample Args*: "2015-04-12 10:00:00", "2017-01-01 00:00:00"

*Default*: no restriction

See **JOIN PERIOD START** for important caveats and a description of how to
format the time. Keep in mind that both **JOIN PERIOD START** and **JOIN PERIOD
END** will override **ALLOW JOINING**- although if the date at which a request
is processed is within the join period, ALLOW JOINING will be used to make the
decision.

**MAX TEAMS**: The max number of (active and inactive) teams allowed to compete
simultaneously.

*Sample Args*: "10", "20", "30"

*Default*: no restriction

Once there are at least MAX TEAMS teams in the league (even if their limit is
0), no new teams will be allowed to join the league. Keep in mind that even
teams that were kicked out of the league (if you're using elimination ladder
settings) will be counted against this.

**MAX ACTIVE TEAMS**: The max number of active teams allowed to compete
simultaneously.

*Sample Args*: "10", "20", "30"

*Default*: no restriction

No new teams will be allowed to join (or become active) as long as there are at
least MAX ACTIVE TEAMS teams in the league with their limit greater than zero.
Keep in mind that if a team becomes inactive, it might be unable to rejoin (or
have to wait) because of this, but it allows you to directly control the number
of teams actually playing in a given league.

### Team Settings

**MIN LIMIT**: The minimum value a team can set for how many games it wants to
be in at once.

*Sample Args*: "0", "1", "5"

*Default*: 0

If you want teams to only be able to compete if they're willing to participate
in at least a certain number of games at once, set the MIN LIMIT to that value.

**MAX LIMIT**: The maximum value a team can set for how many games it wants to
be in at once.

*Sample Args*: "5", "10", "20"

*Default*: None

If you want to avoid teams from flooding the league to the extent that they
match up with everyone else simultaneously, etc., or to keep trolls from
joining your league with their Limit to a really high number of games they
don't intend to actually play (to spam Warlight or to overload your league),
you can set this to a specific value (highly recommended).

**CONSTRAIN LIMIT**: Whether to constrain limits to a specific range instead of
rejecting a set\_limit order (or add\_team order with an inappropriate limit).

*Possible Args*: "TRUE", "FALSE"

*Default*: True

If a team tries to set their limit too high, constraining the limit will cause
it to be just set to the league **MAX LIMIT**. If it's too low, it becomes the
**MIN LIMIT**. To avoid springing surprises on teams, cslbot will not
automatically adjust teams' limits if the league's minimum/maximum limits get
changed.

**PLAYER TEAM LIMIT**: Maximum number of teams a player can join within the
same league (integer).

*Sample Args*: "1", "5", "10"

*Default*: No limit

The CSL framework supports leagues that allow players to join multiple teams as
long as those players don't contain the same players (so you can't have two
teams of the same X players- and, as a side-effect, multi-teaming is not
supported in leagues where the **TEAM SIZE** is 1). You can set an upper limit
to keep players from joining too many teams.

### Vetos and Drops

If a game has been in the lobby too long (past the **EXPIRY THRESHOLD**) with
no one accepting their invite or has had all of its players Vote to End, it
will be considered abandoned. This gives players a mechanism to veto
templates/games they dislike- vetoing makes players less likely to be assigned
to the game's template in the future so it gives them a democratic way to weed
out bad templates. Vetos must be mutual- i.e., **all** teams in a game must
vote to end, decline, or simply not accept their invite (for long enough) in
order for a veto to take effect. If only some teams decline or hang around in
the lobby too long, the game will be counted as a loss against them. A single
player on a team can decline/veto on behalf of the whole team (but votes to end
are not counted unless the game is finished by voting to end).

Players are also able to simply directly *drop* templates- i.e., prevent
themselves from ever playing on a given template- by using the drop\_template
order.

**VETO LIMIT**: Maximum number of vetos per game. (Must be an integer.)

*Sample Args*: "0", "1", "10"

*Default*: 0

Every team a veto occurs, the game is recreated with the same teams (but a
different template, of course). That is, until/unless the game has exceeded its
veto limit, in which case the **VETO PENALTY** will be applied to every team's
rating. If the veto limit is exceeded, the game will also be deleted and no
attempts will be made to recreate it on a different template.

**VETO PENALTY**: Penalty for exceeding the veto limit. (Must be an integer.)

*Sample Args*: "0", "10", "100"

*Default*: 25 for Elo, Glicko, TrueSkill; 1 for win count; 50 for winrate

If teams veto a game too many times (or if they try to veto even though vetoing
isn't enabled in a given league), their ratings will be reduced by the veto
penalty.

**DROP LIMIT**: The maximum number of templates a team can drop (integer).

*Sample Args*: "0", "5", "10"

*Default*: 0

Teams will not be able to drop more than a certain number of templates (given
by the DROP LIMIT) and the drop limit cannot be set so high that it allows
players to simply drop *all* templates in a league. If a team hits its limit,
it can simply use the undrop\_template command to bring that number down.

Be careful about reducing the number of active templates too much (or removing
templates outright) because team Drops will not be automatically updated and
you will risk the possibility that a team has actually dropped all available
templates. (If this happens, you can manually remove their Drops in the team
data sheet for the league.)

### Rating System Configuration

### Elo

**ELO K**: Elo k-Factor (integer)

*Sample Args*: "10", "20", "32"

*Default*: 32

The k-Factor controls the impact a single game can have on a team's rating. If
the k-Factor is 32, the team's rating can change by at most 32 points based on
the result of that game- so higher k-Factors will lead to more fluctuation in a
team's rating.

**ELO DEFAULT**: Default Elo rating (integer)

*Sample Args*: "1000", "1500", "2000"

*Default*: 1500

This the rating new teams start out with. In Elo, the sum of ratings in a given
league is just the default rating * the number of teams (although rounding
errors can come into play). There isn't really much of an impact in what
specific value you choose for the default rating beyond visuals/cosmetics, so
pick whatever makes your league's ratings easier to parse. Try to have a good
ratio between the default rating and the k-Factor so your ratings look
"normal."

### Glicko

**GLICKO RD**: Default Glicko rating deviation (integer)

*Sample Args*: "100", "350", "500"

*Default*: 350

Each Glicko rating is basically a distribution defined by an expected rating
and the rating distribution that defines the range the team's actual rating
might fall within. This is just the default rating deviation all new teams will
begin with, to be generally narrowed as the league progresses and we become
more certain of where their actual skill falls.

**GLICKO DEFAULT**: Default Glicko rating (integer)

*Sample Args*: "1000", "1500", "2000"

*Default*: 1500

This is just the rating new teams start out with. If you plan on modifying it,
try keeping the **GLICKO RD** at the same ratio as it is in the default
settings.

### TrueSkill

**TRUESKILL SIGMA**: Default TrueSkill sigma/standard deviation (integer)

*Sample Args*: "300", "500", "1000"

*Default*: 500

The TrueSkill sigma defines the range within which a team's actual rating
is expected to fall. The recommended value is 1/3 of the **TRUESKILL MU**
value.

**TRUESKILL MU**: Default TrueSkill mu/expected rating (integer)

*Sample Args*: "1000", "1500", "2000"

*Default*: 1500

The TrueSkill mu defines the expected rating for a team, and this is what new
teams get to start out with.

### All Rating Systems

**PREFER SKEWED MATCHUPS**: Whether to prefer matchups with high skill
variation.

*Possible Args*: "TRUE", "FALSE"

*Default*: False

If you want to protect high-rated/skilled teams, set this to True. Otherwise,
games with high parity between teams- i.e., good matches- will be preferred.
This might be useful for leagues where the rating system is based on win
count/win rate and you want to avoid regression to the mean.

### Elimination Ladders

You can use a minimum rating threshold or percentile to weed out teams that
have been at the bottom of the league for a certain amount of time. It's
recommend that you set **ALLOW REMOVAL** to false so that these teams can't
remove all evidence of their participation and rejoin your league. That's the
default value anyway, so if you don't specifically set it to true, you should
be good.

**MIN RATING**: The minimum rating for a team to participate in good standing
(integer).

*Sample Args*: "1000", "1500", "1800"

*Default*: no minimum

You can weed out teams below a certain official rating (using a single rating
score, so no deviations/etc.) for a certain period of time. So if you're
running an Elo ladder and decide that any team that's been below 1500 for 5
days in a row doesn't belong in the league, you can set this to 1500 and
**GRACE PERIOD** to 5. If you set a **MIN RATING PERCENTILE**, it will override
this.

**GRACE PERIOD**: The number of *days* in a row by which a team can be below
the minimum rating/percentile (integer).

*Sample Args*: "0", "1", "3", "5"

*Default*: 0 (no grace period)

Once a team falls below the minimum rating threshold or percentile, it's still
able to recover for the duration of the grace period. It's recommended that you
consider your league speed when setting this- if your league moves slowly, give
times some time to recover (unless you don't want them to be able to recover
once they fall below the threshold). Also keep in mind that some players might
deliberately stall in an Elimination ladder if their opponents are within their
grace period, so try and watch for that.

**RESTORATION PERIOD**: Number of *days* after which an inactive removed team
will have its rating restored to the league default (integer).

*Sample Args*: "5", "10", "30"

*Default*: no restoration

Forever is a long time. If a team has been removed for having a rating that was
below the league threshold, you can restore its rating to the league default
after a certain number of days to give it a chance to compete again.

If you want to set up a promotion/relegation league as an elimination ladder,
you can use this to allow teams that were knocked down to eventually climb back
up (although this would be a function of time rather than a function of their
performance in lower leagues- but you can resolve that by using the **ALLOWED
PLAYERS** command to only allow players from the top N teams in the league
directly below to compete; you'd have to use a formula that also let players on
existing active teams to remain- so all players in non-probation teams in the
current league + players from the top N teams in the league directly below).

**MIN RATING PERCENTILE**: Minimum percentile for a team to participate in good
standing.

*Sample Args*: "10", "15", "35.5"

*Default*: 0 (no minimum)

If you want to regularly cut out the bottom x% of your league, just set your
MIN RATING PERCENTILE to that same x. While using just **MIN RATING** will also
eventually cull your league down (assuming you don't allow any new players to
join- see **ALLOW JOINING**, **JOIN PERIOD START**, and **JOIN PERIOD END**) to
just its top member, it's not going to be as fast since after each culling it
will take teams longer and longer to fall from their higher ratings to your
rating threshold. This allows you to set a dynamic threshold to speed things
up. Keep in mind that it's a bad idea to set this to "50" or below because that
would cull the bottom half of your league very quickly and also mean that the
*average* team (including new teams that just joined) would immediately be on
probation (in their **GRACE PERIOD**).

**MAX RANK**: Maximum rank for a team to continue participating in good
standing.

*Sample Args*: "5", "10", "15"

*Default*: no maximum

If you want to just allow the top N teams in the league to continue competing
in good standing, supply a value for MAX RANK. Any team that's out of the top N
long enough will be culled from the league- so you can make things
particularly exciting and force teams to constantly compete for the top N
spots.

**MIN GAMES TO CULL**: Minimum games before a team can be eliminated.

*Sample Args*: "5", "10", "15"

*Default*: 0 (no minimum)

This way, you can guarantee teams at least N finished games before they run the
risk of probation. This reduces the impact of random early rating fluctuations
and makes the league less hectic for teams just starting out. If you want to
set the minimum *number of days* before a team has to worry about elimination,
use the **GRACE PERIOD**.
