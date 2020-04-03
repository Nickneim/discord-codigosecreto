from PIL import Image, ImageDraw, ImageFont
import discord
import asyncio
from random import sample, choice, shuffle
from discord.ext import commands
from typing import List, Set, Dict, Union
from discord.utils import escape_markdown
import io


SMALL_FONT = ImageFont.truetype("fonts/Open_Sans/OpenSans-Bold.ttf", 14)
MEDIUM_FONT = ImageFont.truetype("fonts/Open_Sans/OpenSans-Bold.ttf", 18)
LARGE_FONT = ImageFont.truetype("fonts/Open_Sans/OpenSans-Bold.ttf", 24)


class GameDoesNotExistError(commands.CheckFailure):
    pass


def game_exists_check(ctx : commands.Context):
    game_cog : GameCog = ctx.bot.get_cog('GameCog')
    if ctx.channel.id not in game_cog.channels:
        raise GameDoesNotExistError()
    return True


class GameStartedError(commands.CheckFailure):
    pass


def game_not_started_check(ctx : commands.Context):
    game_cog : GameCog = ctx.bot.get_cog('GameCog')
    if ctx.channel.id not in game_cog.channels:
        return True
    game : CodigoSecreto = game_cog.channels[ctx.channel.id]
    if game.started:
        raise GameStartedError()
    return True


class NotEnoughPlayersError(commands.CheckFailure):
    pass


def enough_players_check(ctx : commands.Context):
    game_cog : GameCog = ctx.bot.get_cog('GameCog')
    try:
        game : CodigoSecreto = game_cog.channels[ctx.channel.id]
    except KeyError:
        raise GameDoesNotExistError()
    if len(game.red_team) < 2 or len(game.blue_team) < 2:
        raise NotEnoughPlayersError()
    return True


class PlayerNotInGameError(commands.CheckFailure):
    pass


def player_in_game_check(ctx : commands.Context):
    game_cog : GameCog = ctx.bot.get_cog('GameCog')
    try:
        game : CodigoSecreto = game_cog.channels[ctx.channel.id]
    except KeyError:
        raise GameDoesNotExistError()
    if ctx.author not in game.players:
        raise PlayerNotInGameError
    return True


class CodigoSecreto():
    def __init__(self, bot : commands.Bot, channel : discord.TextChannel):
        self.bot : commands.Bot = bot
        self.channel : discord.TextChannel = channel
        self.players : Set[discord.Member] = set()
        self.red_team : Set[discord.Member] = set()
        self.blue_team : Set[discord.Member] = set()
        self.red_spymaster : discord.Member = None
        self.blue_spymaster : discord.Member = None
        self.blue_agents : int = 0
        self.red_agents : int = 0
        self.board : List[int] = []
        self.revealed : List[bool] = []
        self.codenames : List[str] = []
        self.turn : int = 1 # 1=blue, 2=red
        self.started : bool = False
        self.stopping : bool = False
        self.board_image : Image.Image = None
        self.board_draw : ImageDraw.Draw = None

    def reveal_type(self, codename_index : int):
        card_width = 600 // 5
        card_height = 400 // 5
        codename_type = self.board[codename_index]
        if codename_type == 0:
            color = "khaki"
        elif codename_type == 1:
            color = "cyan"
        elif codename_type == 2:
            color = "red"
        else:
            color = "black"
        x = codename_index % 5
        y = codename_index // 5
        x0, y0 = x * card_width, y * card_height
        x1, y1 = x0 + card_width - 1, y0 + card_height - 1
        self.board_draw.rectangle((x0, y0, x1, y1), color, "black", 1)


    def draw_board(self, spymaster=False):
        image = Image.new("RGB", (600, 400))
        draw = ImageDraw.Draw(image)
        card_width = 600 // 5
        card_height = 400 // 5

        for y in range(5):
            for x in range(5):
                codename_index = y * 5 + x
                codename_type = self.board[codename_index]
                text = self.codenames[codename_index].title()
                if not spymaster:
                    color = "white"
                    font_color = "black"
                elif codename_type == 0:
                    color = "khaki"
                    font_color = "black"
                elif codename_type == 1:
                    color = "cyan"
                    font_color = "black"
                elif codename_type == 2:
                    color = "red"
                    font_color = "black"
                else:
                    color = "black"
                    font_color = "white"

                x0, y0 = x * card_width, y * card_height
                x1, y1 = x0 + card_width - 1, y0 + card_height - 1
                draw.rectangle((x0, y0, x1, y1), color, "black", 1)

                font = LARGE_FONT
                font_width, font_height = draw.textsize(text, font)
                font_height += 8
                if font_width + 6 >= card_width:
                    font = MEDIUM_FONT
                    font_width, font_height = draw.textsize(text, font)
                if font_width + 6 >= card_width:
                    font = SMALL_FONT
                    font_width, font_height = draw.textsize(text, font)
                font_x = x * card_width + (card_width - font_width) // 2
                font_y = y * card_height + (card_height - font_height) // 2
                draw.text((font_x, font_y), text, font_color, font)
        return image, draw


    async def send_board_image(self):
        with io.BytesIO() as f:
            try:
                self.board_image.save(f, format='png')
            except IOError:
                return await self.channel.send("No se pudo crear la imagen del mapa.")
            f.seek(0)
            await self.channel.send(file=discord.File(f, filename='board.png'))


    async def new_spymaster(self, spymaster : discord.Member):
        if spymaster in self.blue_team:
            self.blue_spymaster = spymaster
            await self.channel.send(escape_markdown(self.blue_spymaster.display_name) +
                                    " es el nuevo jefe de espías del equipo azul.")
        elif spymaster in self.red_team:
            self.red_spymaster = spymaster
            await self.channel.send(escape_markdown(self.red_spymaster.display_name) + 
                                    " es el nuevo jefe de espías del equipo rojo.")
        else:
            await self.channel.send(f"{escape_markdown(spymaster.display_name)} no está en ningún equipo.")


    async def add_player(self, player : discord.Member,
                         red_team : bool = False):
        self.players.add(player)
        if red_team:
            self.red_team.add(player)
            await self.channel.send(f"{escape_markdown(player.display_name)} se ha unido al equipo rojo")
            if self.red_spymaster is None:
                await self.new_spymaster(player)
        else:
            self.blue_team.add(player)
            await self.channel.send(f"{escape_markdown(player.display_name)} se ha unido al equipo azul")
            if self.blue_spymaster is None:
                await self.new_spymaster(player)

    
    async def remove_player(self, player : discord.Member):
        self.players.remove(player)
        try:
            self.red_team.remove(player)
        except KeyError:
            pass
        try:
            self.blue_team.remove(player)
        except KeyError:
            pass
        if self.blue_spymaster == player:
            self.blue_spymaster = None
            if self.blue_team:
                new_spymaster = choice(list(self.blue_team))
                await self.new_spymaster(new_spymaster)
            else:
                await self.channel.send("El equipo azul ya no tiene jefe de espías.")
        if self.red_spymaster == player:
            self.red_spymaster = None
            if self.red_team:
                new_spymaster = choice(list(self.red_team))
                await self.new_spymaster(new_spymaster)
            else:
                await self.channel.send("El equipo rojo ya no tiene jefe de espías.")
        await self.channel.send(f"{escape_markdown(player.display_name)} ha abandonado la partida.")


    def get_current_spymaster(self):
        if self.turn == 1:
            return self.blue_spymaster
        else:
            return self.red_spymaster
    
    def get_current_team(self):
        if self.turn == 1:
            return self.blue_team
        else:
            return self.red_team


    def is_valid_clue(self, message : discord.Message):
        if message.channel != self.channel or message.author != self.get_current_spymaster():
            return False
        message_words = message.content.split()
        if len(message_words) != 2:
            return False
        clue, amount = message_words
        try:
            amount = int(amount)
        except ValueError:
            return False
        if amount < 0:
            return False
        clue = clue.lower()
        if clue in self.codenames and not self.revealed[self.codenames.index(clue)]:
            return False
        return True

    def is_valid_codename(self, message : discord.Message):
        if message.channel != self.channel or message.author not in self.get_current_team():
            return False
        if message.author == self.get_current_spymaster():
            return False
        answer = message.content.strip().lower()
        if answer == "pasar turno":
            return True
        if answer not in self.codenames:
            return False
        if self.revealed[self.codenames.index(answer)]:
            return False
        return True

    async def round(self):
        spymaster = self.get_current_spymaster()

        await self.channel.send(f"**{escape_markdown(spymaster.display_name)}**, dí una palabra y un número")
        message = await self.bot.wait_for('message', check=self.is_valid_clue)
        await message.add_reaction("✅")

        _, amount = message.content.split()
        try:
            amount = int(amount)
            if amount == 0:
                amount = -1
        except ValueError:
            amount = -1
        await self.channel.send("Ahora tu equipo debe encontrar tus espías.")
        codename_type = self.turn
        can_skip_turn : bool = False
        while codename_type == self.turn and amount != 0 and not self.stopping:
            if can_skip_turn:
                await self.channel.send("Puedes continuar adivinando o `pasar turno`")
            message = await self.bot.wait_for('message', check=self.is_valid_codename)
            codename = message.content.strip().lower()
            if codename == "pasar turno":
                if can_skip_turn:
                    break
                await self.channel.send("Tienes que adivinar al menos una palabra")
                continue
            can_skip_turn = True
            codename_index = self.codenames.index(codename)
            self.revealed[codename_index] = True
            codename_type = self.board[codename_index]
            if codename_type == 0:
                await self.channel.send(f"{codename.title()} es un civil")
            elif codename_type == 1:
                self.blue_agents -= 1
                await self.channel.send(f"{codename.title()} es un agente azul")
            elif codename_type == 2:
                self.red_agents -= 1
                await self.channel.send(f"{codename.title()} es un agente rojo")
            elif codename_type == 3:
                await self.channel.send(f"{codename.title()} es un asesino!")
                self.stopping = True
            else:
                await self.channel.send(f"{codename.title()} es de tipo {codename_type} (BUG)")

            self.reveal_type(codename_index)
            await self.send_board_image()
            amount -= 1

            if self.blue_agents == 0 or self.red_agents == 0:
                self.stopping = True

        if self.turn == 1:
            self.turn = 2
        else:
            self.turn = 1
        
        if self.blue_agents == 0:
            return 1
        elif self.red_agents == 0:
            return 2
        elif codename_type == 3:
            return self.turn
    
    async def start(self, wordlist : List[str]):
        self.codenames = sample(wordlist, 25)
        self.revealed = [False] * 25
        self.board = [0] * 7 + [1] * 8 + [2] * 8 + [3] + [choice((1, 2))]
        shuffle(self.board)
        self.blue_agents = len([x for x in self.board if x == 1])
        self.red_agents = len([x for x in self.board if x == 2])
        if self.blue_agents >= self.red_agents:
            self.turn = 1
        else:
            self.turn = 2

        spymaster_board_image, _ = self.draw_board(spymaster=True)
        self.board_image, self.board_draw = self.draw_board(spymaster=False)
        with io.BytesIO() as f:
            try:
                spymaster_board_image.save(f, format='png')
            except IOError:
                return await self.channel.send("No se pudo crear la imagen del mapa de jefe de espías")
            f.seek(0)
            await self.blue_spymaster.send(file=discord.File(f, filename='spymaster_board.png'))
            f.seek(0)
            await self.red_spymaster.send(file=discord.File(f, filename='spymaster_board.png'))
        await self.send_board_image()
        self.started = True
        self.stopping = False
        while not self.stopping:
            result = await self.round()
        return result



class GameCog(commands.Cog):

    wordlist = []
    with open("cogs/wordlist.txt", encoding='utf-8') as f:
        for line in f:
            wordlist.append(line.strip().lower())


    def __init__(self, bot):
        self.bot = bot
        self.channels : Dict[int, CodigoSecreto] = {}


    @commands.command()
    async def pruebatumismo(self, ctx):
        await ctx.send("Las figuras de cuatro lados se llaman cuadriláteros. Pero los lados tienen que ser rectos, y la figura tiene que ser bidimensional. Prueba tú mismo ...")


    @commands.check(game_not_started_check)
    @commands.guild_only()
    @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    @commands.command(aliases=["unirse"])
    async def join(self, ctx : commands.Context, team : str = None):
        channel_id : int = ctx.channel.id
        if channel_id not in self.channels:
            game : CodigoSecreto = CodigoSecreto(self.bot, ctx.channel)
            self.channels[channel_id] = game
        else:
            game : CodigoSecreto = self.channels[channel_id]
        
        if ctx.author in game.players:
            return await ctx.send("Ya estás en la partida.")

        if team is not None and team.strip().lower() not in ["red", "blue", "azul", "rojo"]:
            return await ctx.send("Ese nombre de equipo no es válido")

        game.players.add(ctx.author)
        if team in ("red", "rojo") or (team is None and len(game.red_team) < len(game.blue_team)):
            await game.add_player(ctx.author, red_team=True)
        else:
            await game.add_player(ctx.author, red_team=False)


    @commands.check(game_not_started_check)
    @commands.check(player_in_game_check)
    @commands.check(game_exists_check)
    @commands.guild_only()
    @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    @commands.command(aliases=["jefe", "boss", "lider", "leader"])
    async def spymaster(self, ctx : commands.Context):
        try:
            game : CodigoSecreto = self.channels[ctx.channel.id]
        except KeyError:
            return await ctx.send("No hay un juego en este canal.")
        if ctx.author not in game.players:
            return await ctx.send("No estás en la partida.")
        else:
            await game.new_spymaster(ctx.author)


    @commands.check(game_not_started_check)
    @commands.check(player_in_game_check)
    @commands.check(game_exists_check)
    @commands.guild_only()
    @commands.command(aliases=["salir"])
    async def leave(self, ctx : commands.Context):
        game : CodigoSecreto = self.channels[ctx.channel.id]
        await game.remove_player(ctx.author)
    

    @commands.check(game_exists_check)
    @commands.guild_only()
    @commands.command(name="players", aliases=["jugadores", "teams", "equipos"])
    async def players_(self, ctx : commands.Context):
        game : CodigoSecreto = self.channels[ctx.channel.id]
        blue_team = ", ".join(("{0}{1}{0}".format("**" if player == game.blue_spymaster else "", player.display_name) for player in game.blue_team))
        red_team = ", ".join(("{0}{1}{0}".format("**" if player == game.red_spymaster else "", player.display_name) for player in game.red_team))
        if not blue_team:
            blue_team = "-"
        if not red_team:
            red_team = "-"
        await ctx.send("Equipo azul: {}\nEquipo rojo: {}".format(blue_team, red_team))


    @commands.check(game_exists_check)
    @commands.guild_only()
    @commands.command(aliases=["detener"])
    async def stop(self, ctx):
        game : CodigoSecreto = self.channels[ctx.channel.id]
        if game.started:
            game.stopping = True
        game.started = False


    @commands.check(enough_players_check)
    @commands.check(game_not_started_check)  # should actually be redundant because of the max_concurrency check
    @commands.check(game_exists_check)
    @commands.guild_only()
    @commands.max_concurrency(1, commands.BucketType.channel)
    @commands.command(aliases=["empezar", "go"])
    async def start(self, ctx):
        game : CodigoSecreto = self.channels[ctx.channel.id]
        result = await game.start(self.wordlist)
        await ctx.send("El juego ha finalizado!")
        if result == 1:
            await ctx.send("¡Victoria para el equipo azul!")
        elif result == 2:
            await ctx.send("¡Victoria para el equipo rojo!")
        else:
            await ctx.send("Victoria para el equipo... " + str(result) + "?")

    @start.after_invoke  # only called if it passes all checks
    async def after_start(self, ctx : commands.Context):
        del self.channels[ctx.channel.id]


    @commands.check(game_not_started_check)
    @commands.check(game_exists_check)
    @commands.command()
    async def reset(self, ctx : commands.Context):
        del self.channels[ctx.channel.id]


    @commands.Cog.listener("on_command_error")
    async def on_command_error(self, ctx : commands.Context, error):
        if isinstance(error, GameDoesNotExistError):
            await ctx.send("No hay un juego en este canal.")
        elif isinstance(error, NotEnoughPlayersError):
            await ctx.send("No hay suficientes jugadores en ambos equipos para empezar el juego.")
        elif isinstance(error, GameStartedError):
            await ctx.send("¡El juego ya ha empezado!")
        elif isinstance(error, PlayerNotInGameError):
            await ctx.send("No estás en la partida.")
        else:
            raise error


def setup(bot):
    bot.add_cog(GameCog(bot))
