from discord.ext import commands
from bot import Parrot
from utils.parrot_embed import ParrotEmbed
from utils.converters import Userlike
from exceptions import FriendlyError


class Registration(commands.Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        with open("assets/privacy-policy.txt", "r") as f:
            self.policy_text = f.read()


    @commands.command(
        aliases=[
            "privacy_policy",
            "privacypolicy",
            "privacy",
            "terms_of_service",
            "termsofservice",
            "tos",
            "terms",
            "eula",
        ],
        brief="View Parrot's privacy policy.",
    )
    @commands.cooldown(2, 4, commands.BucketType.user)
    async def policy(self, ctx: commands.Context) -> None:
        """
        View Parrot's privacy policy.
        Parrot collects the message history of registered users to imitate them. Learn more about Parrot's data collection practices here.
        """
        embed = ParrotEmbed(title="Privacy Policy", description=self.policy_text)
        embed.set_footer(
            text=f"{self.bot.command_prefix}register • {self.bot.command_prefix}unregister"
        )
        await ctx.send(embed=embed)


    @commands.command(aliases=["agree", "accept", "initiate", "initate"], brief="Register with Parrot.")
    @commands.cooldown(2, 4, commands.BucketType.user)
    async def register(self, ctx: commands.Context, who: Userlike=None) -> None:
        """
        Register to let Parrot imitate you.
        By registering you agree to Parrot's privacy policy.
        """
        if who is not None and who.id != ctx.author.id:
            raise FriendlyError("You can only register yourself.")

        await self.bot.registered_users.add(ctx.author.id)

        embed = ParrotEmbed(
            title="✅ Registered!",
            color_name="green",
            description="Now Parrot can start learning your speech patterns and imitate you.",
        )
        embed.add_field(
            name="Tip:",
            value=f"If this is your first time registering (or if you deleted your data recently), you might want to consider running the `{self.bot.command_prefix}quickstart` command to immediately give Parrot a dataset to imitate you from. This will scan your past messages to create a model of how you speak, so you can start using Parrot right away.",
        )

        await ctx.send(embed=embed)

    @commands.command(aliases=["disagree", "unaccept", "uninitiate", "uninitate"], brief="Unregister with Parrot.")
    @commands.cooldown(2, 4, commands.BucketType.user)
    async def unregister(self, ctx: commands.Context, who: Userlike=None) -> None:
        """
        Remove your registration from Parrot.
        Parrot will stop collecting your messages and will not be able to imitate you until you register again.
        """
        if who is not None and who.id != ctx.author.id:
            raise FriendlyError("You can only unregister yourself.")

        await self.bot.registered_users.remove(ctx.author.id)

        embed = ParrotEmbed(
            title="Unregistered!",
            color_name="gray",
            description=f"Parrot will no longer be able to imitate you, and it has stopped collecting your messages.\n\n_If you're done with Parrot and don't want it to have your messages anymore, or if you just want a fresh start, you can do `{self.bot.command_prefix}forget me` and your existing data will be permanently deleted from Parrot._",
        )

        await ctx.send(embed=embed)

    @commands.command(
        aliases=[
            "registration_status",
            "registrationstatus",
            "registration",
            "checkregistration",
            "check_registration",
        ],
        brief="Check if you're registered with Parrot.",
    )
    @commands.cooldown(2, 4, commands.BucketType.user)
    async def status(self, ctx: commands.Context) -> None:
        """
        Check if you're registered with Parrot.
        You need to be registered for Parrot to be able to analyze your messages and imitate you.
        """
        if await self.bot.registered_users.has(ctx.author.id):
            await ctx.send("✅ You are currently registered with Parrot.")
        else:
            await ctx.send("❌ You are not currently registered with Parrot.")


def setup(bot: Parrot) -> None:
    bot.add_cog(Registration(bot))
