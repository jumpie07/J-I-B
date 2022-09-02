import interactions
import json
import requests
from sys import exit

# try to load necessary variables of bot -> if Error set to default
try:
    with open("./data/server_datas.json", "r") as sI:
        servers: dict = json.load(sI)

except Exception as e:
    print(f"\n\033[91m[ERROR]:\033[00m Error occurred on loading JSON-File with the server datas.\nError-Code: {e}\n")
    # if cant loaded
    exit()

# set Variables
guild_ids = [servers[server]["id"] for server in servers]  # server ids
muted_users = []  # list of user who muted

# define Bot client variable
bot = interactions.Client(token="your token",
                          intents=interactions.Intents.DEFAULT | interactions.Intents.GUILD_MEMBERS,
                          presence=interactions.ClientPresence(
                              activities=[interactions.PresenceActivity(
                                  name="/help",
                                  type=interactions.PresenceActivityType.GAME)],
                              status=interactions.StatusType.ONLINE
                          )
                          )


# ======================================================================================================================
# ON-READY event
@bot.event
async def on_ready():
    print("\n\033[92m[INFO]:\033[00m Bot successfully started!\n")

    # Total and Online Member counters
    try:
        guild = await interactions.get(bot, interactions.Guild, object_id=931944391768170516)
        total_member_channel = await interactions.get(bot, interactions.Channel, object_id=932174956937228298)

        # derzeit nicht möglich online status eines users abzufragen
        ### online_member_channel = await get(bot, interactions.Channel, channel_id=932174992853061662)
        ### members = await guild.get_all_members()

        await total_member_channel.set_name(f'Total Members: {guild.member_count}')
    except Exception as e:
        print(f"\n\033[91m[ERROR]:\033[00m Error occurred on setting name for Members-Channel"
              f"\nError-Code: {e}\n")


# ======================================================================================================================
# ON_INVITE event
@bot.event
async def on_guild_create(ctx: interactions.Guild):
    if not ctx.id in guild_ids:
        # new entry in server_datas.json
        servers.update({ctx.name: {"id": int(ctx.id), "warns": {}, "rules": {}}})
        with open("./data/server_datas.json", "w") as sI:
            json.dump(servers, sI, indent=4)
        # Send welcome message
        embed = interactions.Embed()
        embed.title = "Hey there! :wave:"
        embed.description = "Hello, thank you for adding me to your Server! Before\
                we can start I need first some informations for handling your Server. \
                Please run following commands to configure your Server: \n\
                • `/set server id` – Copy the server id by right-clicking on the server \
                in the Serverlist on the left side of your screen\n\
                • `/set member role id` – Set the id of the role you want to give users \
                after applying to the Serverrules\n\n **Thank you thats all, have fun!**"
        embed.color = int(('#%02x%02x%02x' % (90, 232, 240)).replace("#", "0x"), base=16)
        channel = await interactions.get(bot, interactions.Channel, object_id=int(ctx.system_channel_id))
        await channel.send(embeds=embed)


# =====================================================================================================================
# RULE System

# -----------------------------------------------------
# ADD RULE ACCEPT button
@bot.command(
    name="add_rule_accept-button",
    description="Define a message that contains the rules",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    options=[
        interactions.Option(
            name="msg_id",
            description="ID of the message",
            type=interactions.OptionType.STRING,
            required=True,
        ),
    ],
)
async def add_rule_accept_button(ctx: interactions.ComponentContext, msg_id):
    # first check if member role is specified for the server
    if "member_role_id" in (servers[ctx.guild.name]).keys():
        msg = await interactions.get(bot, interactions.Message, parent_id=int(ctx.channel_id), object_id=int(msg_id))
        button = interactions.Button(style=interactions.ButtonStyle.SUCCESS, label="Accept",
                                     custom_id="add_member_role")
        await msg.edit(components=button)
        await ctx.send("Setup successfully", ephemeral=True)
    else:
        await ctx.send("You first need to specify a role for this button. Use /set_rule_role for this.", ephemeral=True)


# -----------------------------------------------------
# RULE-BUTTON component
# Component for the Accept-Button -> called if clicked
@bot.component("add_member_role")
async def func(ctx: interactions.ComponentContext):
    member_role_id = servers[ctx.guild.name]["member_role_id"]
    # check if user has role or not
    if (ctx.author.roles is None) or (not (member_role_id in ctx.author.roles)):
        # if not add role to user
        await ctx.author.add_role(member_role_id, int(ctx.guild_id))
        await ctx.send("Now you can use the Server", ephemeral=True)
    else:
        # if already has, send only a message to the user
        await ctx.send("You already have this role!", ephemeral=True)


# -----------------------------------------------------
# RULE-ROLE-SET command
@bot.command(
    name="set_rule_role",
    description="Set the rule that a member get if he accept to the roles",
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    scope=guild_ids,
    options=[
        interactions.Option(
            name="role",
            description="Specifys the role, members will get if react to Rule-Accept-Button",
            type=interactions.OptionType.ROLE,
            requierd=True
        ),
    ],
)
async def set_rule_role(ctx: interactions.CommandContext, role: interactions.Role):
    servers[ctx.guild.name].update({"member_role_id": int(role.id)})
    with open("./data/server_datas.json", "w") as sI:
        json.dump(servers, sI, indent=4)
    await ctx.send("Successfully set role as standard Member role", ephemeral=True)


# -----------------------------------------------------
# ADD RULE command ( for add rules to servers )
@bot.command(
    name="add_rule",
    description="Add a new rule to the server",
    scope=guild_ids,
    options=[
        interactions.Option(
            name="title",
            description="The Title of the rule",
            type=interactions.OptionType.STRING,
            required=True,
        ),
        interactions.Option(
            name="content",
            description="The content of the rule",
            type=interactions.OptionType.STRING,
            required=True,
        ),
    ],
)
async def add_rule(ctx: interactions.CommandContext, title: str, content: str):
    servers[ctx.guild.name]["rules"].update({title: content})
    with open("./data/server_datas.json", "w") as sI:
        json.dump(servers, sI, indent=4)
    await ctx.send(f"Rule {title} was successfully added to Serverrules!", ephemeral=True)


# -----------------------------------------------------
# REMOVE RULE command ( remove a rule from servers )
@bot.command(
    name="remove_rule",
    description="Remove a rule from the server",
    scope=guild_ids,
    options=[
        interactions.Option(
            name="title",
            description="The Title of the rule",
            type=interactions.OptionType.STRING,
            required=True,
        )
    ],
)
async def remove_rule(ctx: interactions.CommandContext, title: str):
    if title in servers[ctx.guild.name]["rules"].keys():
        servers[ctx.guild.name]["rules"].pop(title)
    with open("./data/server_datas.json", "w") as sI:
        json.dump(servers, sI, indent=4)
    await ctx.send(f"Rule {title} was successfully removed from Serverrules!", ephemeral=True)


# -----------------------------------------------------
# ADD RULES DESCRIPTION command
@bot.command(
    name="add_rule_description",
    description="Add a description to your Serverrules",
    scope=guild_ids,
    options=[
        interactions.Option(
            name="content",
            description="Content of the description",
            type=interactions.OptionType.STRING,
            required=True,
        )
    ],
)
async def add_description(ctx: interactions.CommandContext, content: str):
    servers[ctx.guild.name].update({"rule_description": content})
    with open("./data/server_datas.json", "w") as sI:
        json.dump(servers, sI, indent=4)
    await ctx.send(f"Description was successfully added to Serverrules!", ephemeral=True)


# -----------------------------------------------------
# REMOVE RULE DESCRIPTION command
@bot.command(
    name="remove_rule_description",
    description="Removes current description from your Serverrules",
    scope=guild_ids
)
async def remove_description(ctx: interactions.CommandContext):
    if not("rule_description" in servers[ctx.guild.name].keys()):
        await ctx.send(f"There is no rule description on this server!", ephemeral=True)
        return
    servers[ctx.guild.name].pop("rule_description")
    with open("./data/server_datas.json", "w") as sI:
        json.dump(servers, sI, indent=4)
    await ctx.send(f"Description was successfully removed from Serverrules!", ephemeral=True)


# -----------------------------------------------------
# RULES command
# send the actually rules
@bot.command(
    name="rules",
    description="Shows the rules of the server",
    scope=guild_ids,
)
async def rules(ctx: interactions.CommandContext):
    if servers[ctx.guild.name]["rules"] == {} and not "rule_description" in servers[ctx.guild.name].keys():
        return await ctx.send("No Rules specified! Please add rules via `/rule_add` or a description via "
                              "`/add_rule_description`– For more infos type `/help`")
    embed = interactions.Embed()
    embed.title = f"Regeln von {ctx.guild.name}"
    if "rule_description" in servers[ctx.guild.name].keys():
        embed.description = servers[ctx.guild.name]["rule_description"]
    for rule in servers[ctx.guild.name]["rules"].keys():
        embed.add_field(rule, servers[ctx.guild.name]["rules"][rule])
    embed.color = int(('#%02x%02x%02x' % (90, 232, 240)).replace("#", "0x"), base=16)
    await ctx.send(embeds=embed)


# ======================================================================================================================
# KICK command
@bot.command(
    name="kick",
    description="Command to kick a user",
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
    scope=guild_ids,
    options=[
        interactions.Option(
            name="user",
            description="User you want to kick",
            type=interactions.OptionType.USER,
            required=True,
        ),
    ],
)
async def kick(ctx: interactions.CommandContext, user: interactions.User):
    await user.kick(ctx.guild_id)
    await ctx.send(f"{user.mention} has been kicked!")


# ======================================================================================================================
# BAN command
@bot.command(
    name="ban",
    description="Command to ban a user",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.BAN_MEMBERS,
    options=[
        interactions.Option(
            name="user",
            description="User you want to ban",
            type=interactions.OptionType.USER,
            required=True,
        ),
        interactions.Option(
            name="reason",
            description="Reason for banning",
            type=interactions.OptionType.STRING,
            required=False,
        ),
    ],
)
async def ban(ctx: interactions.CommandContext, user: interactions.User, reason: str = None):
    if reason:
        await ctx.guild.ban(user, reason=reason)
        return await ctx.send(f"{user} has been banned because {reason}!")
    else:
        await ctx.guild.ban(user)
        return await ctx.send(f"{user} has been banned")


# ======================================================================================================================
# UNBAN command
@bot.command(
    name="unban",
    description="Command to unban a user",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.BAN_MEMBERS,
    options=[
        interactions.Option(
            name="user",
            description="User you want to unban",
            type=interactions.OptionType.USER,
            required=True,
        )
    ],
)
async def unban(ctx: interactions.CommandContext, user):
    await ctx.guild.remove_ban(user)
    await ctx.send(f"has been unbanned!")


# ======================================================================================================================
# ADD-ROLE command
@bot.command(
    name="add_role",
    description="Command to assign a role to a user",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    options=[
        interactions.Option(
            name="user",
            description="User you want to assign a role to",
            type=interactions.OptionType.USER,
            required=True,
        ),
        interactions.Option(
            name="role",
            description="Role you want to assign",
            type=interactions.OptionType.ROLE,
            required=True,
        ),
    ],
)
async def add_role(ctx: interactions.CommandContext, user: interactions.User, role: interactions.Role):
    # check if the user already has this role
    if role.id in user.roles:
        await ctx.send(f"{user.mention} already has the role {role.name}!", ephemeral=True)
        return
    # assign the role
    await user.add_role(role, ctx.guild_id)
    await ctx.send(f"{user.mention} has been given the role {role.name}!")


# ======================================================================================================================
# REMOVE-ROLE command
@bot.command(
    name="remove_role",
    description="Command to remove a role from a user",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    options=[
        interactions.Option(
            name="user",
            description="User you want to remove a role from",
            type=interactions.OptionType.USER,
            required=True,
        ),
        interactions.Option(
            name="role",
            description="Role you want to remove",
            type=interactions.OptionType.ROLE,
            required=True,
        ),
    ],
)
async def remove_role(ctx: interactions.CommandContext, user: interactions.User, role: interactions.Role):
    # check if the user does not have the role
    if not (role.id in user.roles):
        await ctx.send(f"{user.mention} doesn't have the role {role.name}!", ephemeral=True)
        return
    # else remove the role
    await user.remove_role(role, ctx.guild_id)
    await ctx.send(f"{user.mention} has been removed the role {role.name}!")


# ======================================================================================================================
# WARN command
@bot.command(
    name="warn",
    description="Command to warn a user",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.KICK_MEMBERS,
    options=[
        interactions.Option(
            name="user",
            description="User you want to warn",
            type=interactions.OptionType.USER,
            required=True,
        ),
        interactions.Option(
            name="reason",
            description="Reason for warning",
            type=interactions.OptionType.STRING,
            required=True,
        ),
    ],
)
async def warn(ctx: interactions.CommandContext, user: interactions.Member, reason: str):
    if user.name == bot.me.name: return await ctx.send("Action not allowed", ephemeral=True)
    if user.name == "Ice Warrior":
        if ctx.author.name in servers[ctx.guild.name]["warns"].keys():
            servers[ctx.guild.name]["warns"][ctx.author.name] += 1
        else:
            servers[ctx.guild.name]["warns"].setdefault(ctx.author.name, 1)
        return await ctx.send(f"Du Kek! Das gibt ne Verwarnung! {ctx.author.mention} was warned for warning Ice! "
                              f"({user.mention} has {servers[ctx.guild.name]['warns'][ctx.author.name]} warns)")

    # check if the user has already been warned
    if user.name in servers[ctx.guild.name]["warns"].keys():
        servers[ctx.guild.name]["warns"][user.name] += 1
    else:
        servers[ctx.guild.name]["warns"].setdefault(user.name, 1)
    # update json file
    with open("./data/server_datas.json", "w") as sI:
        json.dump(servers, sI, indent=4)
    # send message
    await ctx.send(f"{user.mention} has been warned for {reason}! ({user.mention}\
    has {servers[ctx.guild.name]['warns'][user.name]} warns)")


# ======================================================================================================================
# MUTE command
@bot.command(
    name="mute",
    description="Command to mute a user",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.MUTE_MEMBERS,
    options=[
        interactions.Option(
            name="user",
            description="User you want to mute",
            type=interactions.OptionType.USER,
            required=True,
        ),
    ],
)
async def mute(ctx: interactions.CommandContext, user: interactions.User):
    await ctx.send(f"{user.mention} has been muted!")
    muted_users.append(user.username)


# ======================================================================================================================
# MESSAGE-DELETE command
@bot.command(
    name="msg_delete",
    description="Deletes all last count messages",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.MANAGE_MESSAGES,
    options=[
        interactions.Option(
            name="count",
            description="Count of messages that should deleted",
            type=interactions.OptionType.INTEGER,
            required=False
        ),
    ],
)
async def msg_delete(ctx: interactions.CommandContext, count: int = 1):
    # check if count is a correct value
    if not isinstance(count, int) or count <= 0:
        return await ctx.send("False input! Value needs to be a number higher the 0", ephemeral=True)

    # get channel and then delete messages using purge-function
    channel = await interactions.get(bot, interactions.Channel, object_id=int(ctx.channel_id))
    await channel.purge(count)  # delete messages
    await ctx.send(f"Deleted last {count} messages in this channel!", ephemeral=True)


# ======================================================================================================================
# MEMBER-STATUS Functionality
@bot.event
async def on_guild_member_add(ctx: interactions.GuildMember):
    # If new user joined Guild -> update Total-member dump
    total_member_channel = await interactions.get(bot, interactions.Channel, object_id=932174956937228298)
    guild = await interactions.get(bot, interactions.Guild, object_id=int(ctx.guild_id))
    await total_member_channel.set_name(f'Total Members: {guild.member_count}')
    sys_channel = await interactions.get(bot, interactions.Channel, object_id=int(guild.system_channel_id))
    embed = interactions.Embed()
    embed.title = f"Welcome to Ice Topia :wave:"
    embed.description = f"Welcome {ctx.mention}! Thank you for join this Server! I hope you have fun here and find \
    some friends :v:"
    embed.color = int(('#%02x%02x%02x' % (90, 232, 240)).replace("#", "0x"), base=16)
    await sys_channel.send(embeds=embed)


@bot.event
async def on_guild_member_remove(ctx):
    # If user left the Guild -> update Total-member dump
    total_member_channel = await interactions.get(bot, interactions.Channel, object_id=932174956937228298)
    memberCount = int(total_member_channel.name.split(": ")[1])  # because ctx is none
    await total_member_channel.set_name(f'Total Members: {memberCount}')


# =====================================================================================================================
# MEME generator command
@bot.command(
    name="meme",
    description="post a random meme",
    scope=guild_ids,
)
async def meme(ctx: interactions.CommandContext):
    async def gen_meme():
        meme_json = requests.get("https://meme-api.herokuapp.com/gimme").text
        loaded = json.loads(meme_json)
        title = loaded["title"]
        url = loaded["url"]
        nsfw = loaded["nsfw"]
        return title, url, nsfw

    nsfw = True
    while nsfw != False:
        title, url, nsfw = await gen_meme()
    await ctx.send(f"**{title}**\n{url}")


# =====================================================================================================================
# HELP command
@bot.command(
    name="help",
    description="Sends help menu to all commands and functions",
    scope=guild_ids,
)
async def help_menu(ctx: interactions.CommandContext):
    # Create Embed Message
    embed = interactions.Embed()
    embed.title = "Help menu of J-I-B Bot – Page 1"
    with open("data/help_doc.json", "r") as fo:
        help_pages: dict = json.load(fo)
    embed.description = help_pages["page1"]["description"]
    for field in help_pages["page1"]["fields"].keys():
        embed.add_field(field, help_pages["page1"]["fields"][field])
    embed.color = int(('#%02x%02x%02x' % (124, 255, 48)).replace("#", "0x"), base=16)

    # Create Next and Last Page button row
    back_btn = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="« Back",
        custom_id="back_button",
    )

    next_btn = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next »",
        custom_id="next_button",
    )

    wiki_btn = interactions.Button(
        style=interactions.ButtonStyle.LINK,
        label="Wiki",
        url="https://github.com/jumpie07/jump-ice-dc.bot/blob/main/wiki.mde",
    )

    row = interactions.ActionRow.new(back_btn, next_btn, wiki_btn)
    await ctx.send(embeds=embed, components=row)

@bot.component("back_button")
async def func(ctx: interactions.ComponentContext):
    # get current page
    cur_page = int(ctx.message.embeds.pop().title.split(" ")[-1])
    # if already at page 1 -> return
    if cur_page == 1:
        await ctx.send("You already at page 1!", ephemeral=True)
        return
    # else load new content into embed
    embed = interactions.Embed()
    embed.title = f"Help menu of J-I-B Bot – Page {cur_page-1}"
    with open("data/help_doc.json", "r") as fo:
        help_pages: dict = json.load(fo)
    if "description" in help_pages[f"page{cur_page-1}"].keys():
        embed.description = help_pages[f"page{cur_page-1}"]["description"]
    if help_pages[f"page{cur_page - 1}"]["fields"].keys():
        for field in help_pages[f"page{cur_page - 1}"]["fields"].keys():
            embed.add_field(field, help_pages[f"page{cur_page - 1}"]["fields"][field])
    embed.color = int(('#%02x%02x%02x' % (124, 255, 48)).replace("#", "0x"), base=16)
    # edit message
    await ctx.edit(embeds=embed)

@bot.component("next_button")
async def func(ctx: interactions.ComponentContext):
    # get current page
    cur_page = int(ctx.message.embeds.pop().title.split(" ")[-1])
    # if already at last page -> return
    with open("data/help_doc.json", "r") as fo:
        help_pages: dict = json.load(fo)
    if len(help_pages) == cur_page:
        await ctx.send("You already at last page!", ephemeral=True)
        return
    # else load new content into embed
    embed = interactions.Embed()
    embed.title = f"Help menu of J-I-B Bot – Page {cur_page+1}"
    if "description" in help_pages[f"page{cur_page+1}"].keys():
        embed.description = help_pages[f"page{cur_page+1}"]["description"]
    for field in help_pages[f"page{cur_page+1}"]["fields"].keys():
        embed.add_field(field, help_pages[f"page{cur_page+1}"]["fields"][field])
    embed.color = int(('#%02x%02x%02x' % (124, 255, 48)).replace("#", "0x"), base=16)
    # edit message
    await ctx.edit(embeds=embed)
    # await ctx.send(embeds=embed)


# =====================================================================================================================
# Test system for SELECT-MENUS

@bot.command(
    name="add_choose_element",
    description="Add a role to the Role choose box. See /help for more infos",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.MANAGE_ROLES,
    options=[
        interactions.Option(
            name="role",
            description="The role you want to add",
            type=interactions.OptionType.ROLE,
            required=True,
        ),
    ],
)
async def test(ctx):
    pass


@bot.command(
    name="add_select_menu",
    description="Only a test function for testing select-menus",
    scope=guild_ids,
    default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    options=[
        interactions.Option(
            name="msg_id",
            description="ID of the message",
            type=interactions.OptionType.STRING,
            required=True,
        ),
    ],
)
async def add_chooser_test(ctx: interactions.ComponentContext, msg_id):
    # get the message
    msg = await interactions.get(bot, interactions.Message, parent_id=int(ctx.channel_id), object_id=int(msg_id))
    # if message not from bot -> return
    if msg.author != bot.me: return await ctx.send("Du bist ein Kek")
    select_test = interactions.SelectMenu(
        options=[
            interactions.SelectOption(
                label="Mitglied",
                value=911297730373120060,
                description="Role for Almans"
            ),
            interactions.SelectOption(
                label="Terraconia Spieler",
                value=911925141594845235,
                description="If you play on Terraconia"
            ),
            interactions.SelectOption(
                label="Kek",
                value=1011224145440292945,
                description="If you be a Kek"
            )
        ],
        placeholder="Wähle deine Rollen",
        custom_id="test_menu_component",
        max_values=3
    )
    await msg.edit(components=select_test)
    await ctx.send("Setup successfully", ephemeral=True)


@bot.component("test_menu_component")
async def func(ctx: interactions.ComponentContext, role_ids: list[str]):
    for roleid in role_ids:
        if not roleid in ctx.author.roles:
            await ctx.author.add_role(int(roleid), int(ctx.guild_id))
    await ctx.send(f"Ausgewählte rollen {role_ids}", ephemeral=True)


bot.start()
