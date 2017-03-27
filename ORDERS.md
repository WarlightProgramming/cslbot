# Orders

## Table of Contents

* [Introduction](#introduction)
* [Structure](#structure)
  * [Threads](#threads)
  * [Syntax](#syntax)
  * [Access Levels](#access-levels)
* [Orders List](#orders-list)
  * [Special Orders](#special-orders)
  * [Normal Orders](#normal-orders)

## Introduction

For the sake of simplicity and ease-of-setup, the CSL framework eschews graphic
interfaces and instead uses public forum threads to create command-line-esque
pseudo-interfaces where users and mods interact using **orders** enclosed in
Warlight's markdown code tags. Since non-graphic interfaces can quickly become
nightmares to navigate, the list of orders is kept minimal and it's
expected that most league configuration will happen using
[commands](COMMANDS.md). To avoid mistakes (such as accidentally applying a
random phrase that merely *looked* like an order), the syntax is kept
relatively strict and orders have to be entered in precise places- each
league cluster (with a common workbook) can only have a single thread where
orders can be submitted. As an abuse-prevention measure, orders are not
processed at all until a thread has posts by at least 5 unique authors and uses
the !validate\_league [special order](#special-orders) to confirm its relation
to the league workbook.

## Structure

### Threads

Orders can only be made in active **order threads**- of which each league
cluster (sharing a workbook) can only have one. Order threads must be
Warlight public forum threads (i.e., viewable without a Warlight login) that:

* have been linked using the **THREAD** command in a league workbook's commands
sheet

* have posts by at least 5 unique authors (until which the thread orders will
  not be processed)

* have a !validate\_league order in the top post of the thread

For a quick primer on the !validate\_league order, see the [special
orders](#special-orders) section of this document.

Keep in mind that a single post is normally only going to be processed once- so
it's strongly advised against to try to get orders in by editing your post. If
the post has already been processed and the **OFFSET** command hasn't been
changed, your post will not be looked at again.

### Syntax

Orders must be entered in code tags and multiline orders should be separated
using newlines. Arguments after the order name must be given in a specific
order (specified by the order itself- see the [orders list](#orders-list) for
information). Multi-word arguments (e.g., team or league names must be
surrounded by double-quotes. For example, if a player wanted to confirm a team
called Master Blaster in a league called The Thunderdome, they would have to
structure their order like this:

'''
confirm\_team "The Thunderdome" "Mad Max"
'''

### Access Levels

The CSL framework supports three different access levels for handling thread
orders- players (i.e., normal users with no special privileges), mods (i.e.,
players given special privileges using the **MODS** command in the command
sheet), and the league admin (the owner of the league cluster, who *must* have a
Warlight membership and ideally should be the owner of the league workbook).
Mods can be specified on a league-by-league basis within a cluster/workbook.
The access levels are strictly hierarchical in the sense that all orders
available to a lower level are also available to any higher levels.

## Orders List

### Special Orders

#### !validate\_league

**Minimum access level**: creator of league order thread (ideally the admin) 

**Syntax**:
'''
!validate\_league <sheetID>
'''

This order **must** be placed in the top (initial) post of the league order
thread. If the league thread changes (by modifying the **THREAD** command),
the new thread also needs a !validate\_league order in its top post.

The sheetID can be obtained from the Google Sheets workbook URL.
For example, if the league were hosted on a workbook with the URL:

'''
https://docs.google.com/spreadsheets/d/SHEETID/edit#gid=TABID
'''

(noet that '/edit' and everything after it can just be removed- they just
specify the tab/worksheet within the workbook)

The !validate\_league order would look like:

'''
!validate\_league SHEETID
'''

#### !BOT\_IGNORE

**Minimum access level**: player

**Syntax**:
'''
!BOT\_IGNORE
'''

This order takes no arguments and causes all orders after it in the same post
to be ignored. It's essentially the equivalent of an escape character for
orders. To un-escape, you can either enter all real orders before the
!BOT\_IGNORE order or simply create a new post with the orders you want to be
processed. The !BOT\_IGNORE order is mainly intended to be used for
demonstrating sample orders, showing order syntax, etc.

### Normal Orders

#### add\_team

**Minimum access level**: player

**Syntax**:
'''
add\_team <leagueName> <teamName> <limit> <players>
'''

This order creates new teams within a league.

The league name and team name should be entered in double quotes if they
consist of more than one word. The limit should be a non-negative integer that
sets the maximum number of games a team is willing to participate in at once.
The league can set a range for limits using the **MAX LIMIT** and **MIN LIMIT**
commands, as well as a minimum limit for a team to get ranked using the **MIN
LIMIT TO RANK** command.

Players should be supplied as a space-separated list of Warlight IDs
(retrievable from profile URLs). For example, if you wanted to create a team
for The Thunderdome called Mad Max with up to 1 game at a time and the
members with the following profile URLs:

https://www.warlight.net/Profile?p=PLAYER1

https://www.warlight.net/Profile?p=PLAYER2

https://www.warlight.net/Profile?p=PLAYER3

You would use the following order:
'''
add\_team "The Thunderdome" "Mad Max" 1 PLAYER1 PLAYER2 PLAYER3
'''

Note that the number of players you enter should match exactly the number of
players per team in the league you're trying to enter, or your order will be
rejected.

#### confirm\_team

**Minimum access level**: player (on the affected team)

**Syntax**:
'''
confirm\_team <leagueName> <teamName>
'''

This order confirms that its author wants to be on the given team. Team
creators do not need to enter this order (they're automatically confirmed
when they add the team). Team will not have any games created for them until
all members are confirmed (in order to avoid abuse/spamming people with games
for teams/leagues they did not actually join). Note that leagues may also limit
the number of teams that a single player can actively participate in- in which
case players should set a 0 limit for any teams they don't intend to continue
participating in (or alternatively, unconfirm those teams). Otherwise players
will simply end up participating in/getting games for the N oldest active teams
they're associated with, N being the maximum number of teams a single player
can participate in.

Mod and admins can also specify player IDs at the end of the order in order to
confirm on behalf of other players (e.g., to confirm a team of which the members can't
figure out how to use thread orders).

#### unconfirm\_team

**Minimum access level**: player (on the affected team)

**Syntax**:
'''
unconfirm\_team <leagueName> <teamName>
'''

Works similarly to confirm\_team, but sets the authoring player's confirmation
to false (and keeps the team from getting any new games). This allows players
to remove themselves from a team and deactivate the team in a way that keeps
anyone else from reactivating the team and adding them back in. Players are
encouraged to use this order instead of set\_limit (which can be easily
reversed without their consent) or remove\_team (which deletes all team data)
to remove themselves from teams in which they no longer intend to participate.

As with confirm\_team, mods and admins can specify player IDs after the team
name if they want to unconfirm on behalf of other players.

#### set\_limit

**Minimum access level**: player (on the affected team)

**Syntax**:
'''
set\_limit <leagueName> <teamName> <limit>
'''

This is a simple order to change the maximum number of games a team can
participate in simultaneously. Players must be on the team affected by the
order in order to use this, although mods and admins can set the limit for
any team.

#### remove\_team

**Minimum access level**: player (on the affected team)

**Syntax**:
'''
remove\_team <leagueName> <teamName>
'''

This order is disabled by default but can be enabled using the **ALLOW
REMOVAL** command in the commands sheet. Players using this order remove the
team's record from the league's team data sheet, wiping its history beyond any
games played (which will no longer affect its rating). If players want to
remove a team and its history so they can get a fresh start (since no two teams
can contain the exact same players), they can use this order to do so.

#### drop\_template

**Minimum access level**: player (on the affected team)

**Syntax**:
'''
drop\_template <leagueName> <teamName> <templateName>
'''

Players can use this order to keep their team from ever playing on that
template again (until/unless te template is undropped by them or one of their
teammates). Leagues can set a **DROP LIMIT** (using the commands sheet),
however, and by default dropping templates is disabled.

Template names must match the official template name in the league's template
data sheet.

If drops are disabled, teams may still be able to use the veto mechanism (in
which all involved teams in a game decline the game, refuse to join, or vote to
end)- although that mechanism is disabled by default too and can incur
penalties on declining teams if they exceed the veto limit for the game or
can't get the other teams to cooperate).

#### undrop\_template

**Minimum access level**: player (on the affected team)

**Syntax**:
'''
drop\_template <leagueName> <teamName> <templateName>
'''

This order reverses the drop\_template order and can be useful if teams want to
try out a template they've avoided in the past or if they simply want to get
below the drop limit again so they can drop a template they want to avoid even
more.

#### activate\_template

**Minimum access level**: mod

**Syntax**:
'''
activate\_template <leagueName> <templateName>
'''

This order activates a template and allows it to be used in new games created
for the league. The template name must exactly match the template name in the
league's template data sheet.

#### deactivate\_template

**Minimum access level**: mod

**Syntax**:
'''
deactivate\_template <leagueName> <templateName>
'''

This order deactivates a template and keeps it from being used in new games
created for the league. It will fail if the league has already reached its minimum
number of active templates.

#### quit\_league

**Minimum access level**: player

**Syntax**:
'''
quit\_league <leagueName>
'''

This is a convenience order for users to be able to quickly unconfirm all teams
they're affiliated with in the league- especially useful when users are on
multiple teams in the same league and are planning on taking a vacation/etc.

As with confirm\_team and unconfirm\_team, mods can use this command on behalf
of other players by simply adding a space-separated list of player names at the
end of the order.
