import discord
from typing import Tuple, List
from redbot.core import checks, commands
from .converters import RoleSyntaxConverter, ComplexActionConverter
from redbot.core.utils.chat_formatting import pagify


class MassManager:
    """
    Mass role operations
    """

    __author__ = "mikeshardmind"
    __version__ = "0.0.8a"

    def __init__(self, bot):
        self.bot = bot

    async def update_roles_atomically(
        self,
        who: discord.Member,
        give: List[discord.Role] = [],
        remove: List[discord.Role] = [],
    ):
        """
        Give and remove roles as a single op
        """
        give = give or []
        remove = remove or []
        roles = [r for r in who.roles if r not in remove]
        roles.extend([r for r in give if r not in roles])
        if sorted(roles) == sorted(who.roles):
            return
        payload = {"roles": [r.id for r in roles]}
        await self.bot.http.request(
            discord.http.Route(
                "PATCH",
                "/guilds/{guild_id}/members/{user_id}",
                guild_id=who.guild.id,
                user_id=who.id,
            ),
            json=payload,
        )

    def all_are_valid_roles(self, ctx, role_dict: dict) -> bool:
        """
        Quick heirarchy check on a role set in syntax returned
        """
        roles = role_dict["+"] + role_dict["-"]
        author = ctx.author
        author_allowed = ctx.guild.owner == author or all(
            ctx.author.top_role > role for role in roles
        )
        bot_allowed = ctx.guild.me.guild_permissions.manage_roles and all(
            ctx.guild.me.top_role > role for role in roles
        )
        return author_allowed and bot_allowed

    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.group(name="massrole", autohelp=True)
    async def mrole(self, ctx: commands.Context):
        """
        Commands for mass role management
        """
        pass

    @mrole.command(name="bots")
    async def mrole_bots(self, ctx: commands.Context, *, roles: RoleSyntaxConverter):
        """
        adds/removes roles to all bots.

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole bots +RoleToGive, -RoleToRemove

        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in ctx.guild.members:
            if member.bot:
                await self.update_roles_atomically(
                    member, give=roles["+"], remove=roles["-"]
                )

        await ctx.tick()

    @mrole.command(name="all")
    async def mrole_all(self, ctx: commands.Context, *, roles: RoleSyntaxConverter):
        """
        adds/removes roles to all users.

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole all +RoleToGive, -RoleToRemove

        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in ctx.guild.members:
            await self.update_roles_atomically(
                member, give=roles["+"], remove=roles["-"]
            )

        await ctx.tick()

    @mrole.command(name="humans")
    async def mrole_humans(self, ctx: commands.Context, *, roles: RoleSyntaxConverter):
        """
        adds/removes roles to all humans.

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole humans +RoleToGive, -RoleToRemove

        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in ctx.guild.members:
            if not member.bot:
                await self.update_roles_atomically(
                    member, give=roles["+"], remove=roles["-"]
                )

        await ctx.tick()

    @mrole.command(name="user")
    async def mrole_user(
        self, ctx: commands.Context, user: discord.Member, *, roles: RoleSyntaxConverter
    ):
        """
        adds/removes roles to a user

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole user Sinbad#0001 +RoleToGive, -RoleToRemove

        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        await self.update_roles_atomically(user, give=roles["+"], remove=roles["-"])

        await ctx.tick()

    @mrole.command(name="in")
    async def mrole_user(
        self, ctx: commands.Context, role: discord.Role, *, roles: RoleSyntaxConverter
    ):
        """
        adds/removes roles to all users with a specified role

        Roles should be comma seperated and preceded by a `+` or `-` indicating
        to give or remove

        You cannot add and remove the same role

        Example Usage:

        [p]massrole in "Red Team" +Champions, -Losers
        """

        if not self.all_are_valid_roles(ctx, roles):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        for member in role.members:
            await self.update_roles_atomically(
                member, give=roles["+"], remove=roles["-"]
            )

        await ctx.tick()

    @mrole.command(name="search")
    async def mrole_search(self, ctx: commands.Context, *, roles: RoleSyntaxConverter):
        """
        Searches for users with the specified role criteria

        Example Usage to find all users in the "Admins" role who are not in
        either of the "bots" or "Blue Team" roles

        [p]massrole search +Admins, -bots, -Blue Team

        Not specifying any `+` roles will still work as will not any `-`

        Example usage to find all users who aren't in the "Read Rules" role:

        [p]massrole search -Read Rules
        """

        members = set(ctx.guild.members)

        for r in roles["+"]:
            members &= set(r.members)
        for r in roles["-"]:
            members -= set(r.members)

        output = "\n".join(
            f'{member} {("(" + member.nick + ")") if member.nick else ""}'
            for member in members
        )

        for page in pagify(output):
            await ctx.send(page)

    @mrole.command(name="complex", hidden=True)
    async def mrole_complex(
        self, ctx: commands.Context, *, query: ComplexActionConverter
    ):
        """
        Basic flags...
        
        --has-all roles
        --has-none roles
        --has-any roles
        --add roles
        --remove roles
        --only-humans
        --only-bots
        --everyone
        """

        apply = {"+": query["add"], "-": query["remove"]}
        if not self.all_are_valid_roles(ctx, apply):
            return await ctx.send(
                "Either you or I don't have the required permissions "
                "or position in the hierarchy."
            )

        members = set(ctx.guild.members)

        if not query["everyone"]:

            if query["bots"]:
                members = {m for m in members if m.bot}
            elif query["humans"]:
                members = {m for m in members if not m.bot}

            for role in query["all"]:
                members &= set(role.members)
            for role in query["none"]:
                members -= set(role.members)

            if query["any"]:
                any_union = set()
                for role in query["any"]:
                    any_union |= set(role.members)
                members &= any_union

        for member in members:
            await self.update_roles_atomically(
                member, give=query["add"], remove=query["remove"]
            )

        await ctx.tick()
