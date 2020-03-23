from PIL import Image, ImageDraw, ImageFont
import discord
import asyncio
from random import sample, choice
from discord.ext import commands

class GameCog(commands.Cog):

    # wordlist = ["Ángel", "Ojo", "Pizza", "Enojado", "Fuegos artificiales", "Calabaza", "Bebé", "Flor", "Arco iris", "Barba", "Platillo volador", "Reciclar", "Biblia", "Jirafa", "Castillo de arena", "Bikini", "Gafas", "Copo de nieve", "Libro", "Tacón", "Escalera", "Cucurucho de helado", "Estrella de mar", "Abejorro", "Iglú", "Fresa", "Mariposa", "Escarabajo", "Sol", "Cámara", "Lámpara", "Neumático", "Gato", "León", "Tostada", "Iglesia", "Buzón", "Cepillo de dientes", "Lápiz de color", "Noche", "Pasta dental", "Delfín", "Nariz", "Camión", "Huevo", "Juegos Olímpicos", "Voleibol", "Torre Eiffel", "Maní", "Beso", "Cerebro", "Cachorro", "Patio de recreo", "Britney Spears", "Baño de burbujas", "Kiwi", "Pastel de calabaza", "Hebilla", "Lápiz labial", "Gota de lluvia", "Autobús", "Langosta", "Robot", "Accidente automovilistico", "Chupete", "Castillo de arena", "Imán", "Zapatilla", "Sierra de cadena", "Megáfono", "Bola de nieve", "Tienda de circo", "Sirena", "Aspersor", "Computadora", "Minivan", "Estatua de la Libertad", "Cuna", "Monte Everest", "Renacuajo", "Dragón", "Música", "Campamento", "Pesa", "Polo Norte", "Telescopio", "Anguila", "Enfermera", "Tren", "Rueda de la fortuna", "Búho", "Triciclo", "Bandera", "Chupete", "Tutú", "Correo no deseado", "Piano", "Ático", "Pegamento", "Reloj de bolsillo", "Asiento trasero", "Silla alta", "Banda de rock", "México", "Cumpleaños", "Hockey", "Piegrande", "Calabozo", "Hotel", "Huevos revueltos", "Tormenta de nieve", "Cuerda de saltar", "Cinturón de seguridad", "Burrito", "Koala", "Ignorar", "Capitán", "Duende", "Eclipse solar", "Candelabro", "Rápido", "Espacio", "Cuna", "Máscara", "Estetoscopio", "Crucero", "Mecánico", "Cigüeña", "Baile", "Mamá", "Bronceado", "Desodorante", "Señor Cara de Papa", "Hilo", "Facebook", "Saturno", "Turista", "Plano", "Plato de papel", "Estados Unidos", "Marco", "Foto", "WIFI", "Luna llena", "Monja", "Zombi", "Juego", "Pirata"]
    wordlist = None
    with open("cogs/wordlist.txt") as f:
        wordlist = f.read().split()


    boards = []
    with open("cogs/codename_boards.txt") as f:
        for board in f:
            boards.append([int(x) for x in board.strip()])

    codename_emojis = ['🔶', '🔵', '🔴', '🔪']

    def __init__(self, bot):
        self.bot = bot
        self.players = []
        self.red_team = []
        self.blue_team = []
        self.red_boss = None
        self.blue_boss = None
        self.blue_agents = 0
        self.red_agents = 0
        self.board = [1, 2, 1, 0, 2, 2, 0, 0, 3, 1, 1, 1, 1, 1, 0, 0, 2, 0, 1, 2, 2, 2, 2, 0, 1]
        self.revealed = [False] * 25
        self.codenames = []
        self.turn = 1  # 1=blue, 2=red
        self.started = False
        self.stopping = False


    small_font = ImageFont.truetype("fonts/Open_Sans/OpenSans-Bold.ttf", 14)
    medium_font = ImageFont.truetype("fonts/Open_Sans/OpenSans-Bold.ttf", 18)
    large_font = ImageFont.truetype("fonts/Open_Sans/OpenSans-Bold.ttf", 24)


    def reveal_type(self, image, codename_index):
        draw = ImageDraw.Draw(image)
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
        draw.rectangle((x0, y0, x1, y1), color, "black", 1)

    def draw_board(self, boss=False):
        image = Image.new("RGB", (600, 400))
        draw = ImageDraw.Draw(image)
        card_width = 600 // 5
        card_height = 400 // 5

        for y in range(5):
            for x in range(5):
                codename_index = y * 5 + x
                codename_type = self.board[codename_index]
                text = self.codenames[codename_index].capitalize()
                if not boss and not self.revealed[codename_index]:
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

                font = self.large_font
                font_width, font_height = draw.textsize(text, font)
                font_height += 8
                if font_width + 6 >= card_width:
                    font = self.medium_font
                    font_width, font_height = draw.textsize(text, font)
                if font_width + 6 >= card_width:
                    font = self.small_font
                    font_width, font_height = draw.textsize(text, font)
                font_x = x * card_width + (card_width - font_width) // 2
                font_y = y * card_height + (card_height - font_height) // 2
                draw.text((font_x, font_y), text, font_color, font)
        return image


    def rotate_board(self):
        new_board = [0] * 25
        for x in range(5):
            for y in range(5):
                new_x = 4 - y
                new_y = x
                new_board[new_y * 5 + new_x] = self.board[y * 5 + x]
        self.board = new_board

    def format_board(self):
        s = "Es el turno del equipo "
        if self.turn == 1:
            s += "azul"
        elif self.turn == 2:
            s += "rojo"
        else:
            s += str(self.turn)
        max_codename_lengths = [max(len(self.codenames[row*5+column]) for row in range(5)) for column in range(5)]
        s = "\n```"
        for row in range(5):
            for column in range(5):
                codename_index = row * 5 + column
                if self.revealed[codename_index]:
                    codename_type = self.board[codename_index]
                    codename = self.codename_emojis[codename_type]
                else:
                    codename = self.codenames[codename_index]
                codename = codename.center(max_codename_lengths[column] - (1 if self.revealed[codename_index] else 0))
                s += "{}. ".format(codename)
            s = s[:-2]
            s += "\n"
        s += "```"
        return s


    async def new_red_boss(self, ctx, new_boss):
        self.red_boss = new_boss
        if self.red_boss is None:
            await ctx.send(f"El equipo rojo ya no tiene jefe")
        else:
            await ctx.send(f"{self.red_boss.display_name} es el nuevo jefe del equipo rojo")


    async def new_blue_boss(self, ctx, new_boss):
        self.blue_boss = new_boss
        if self.blue_boss is None:
            await ctx.send(f"El equipo azul ya no tiene jefe")
        else:
            await ctx.send(f"{self.blue_boss.display_name} es el nuevo jefe del equipo azul")


    @commands.command()
    async def pruebatumismo(self, ctx):
        await ctx.send("Las figuras de cuatro lados se llaman cuadriláteros. Pero los lados tienen que ser rectos, y la figura tiene que ser bidimensional. Prueba tú mismo ...")


    @commands.guild_only()
    @commands.command(aliases=["unirse"])
    async def join(self, ctx, team : str = None):
        if self.started:
            return await ctx.send("¡El juego ya empezó! Esperá a que termine la partida actual.")
        if ctx.author in self.players:
            return await ctx.send("Ya estás en la partida.")

        if team is not None and team.strip().lower() not in ["red", "blue", "azul", "rojo"]:
            return await ctx.send("Ese nombre de equipo no es válido")

        self.players.append(ctx.author)
        if team in ("red", "rojo") or (team is None and len(self.red_team) < len(self.blue_team)):
            self.red_team.append(ctx.author)
            await ctx.send(f"{ctx.author.display_name} se ha unido al equipo rojo")
            if self.red_boss is None:
                await self.new_red_boss(ctx, ctx.author)
        else:
            self.blue_team.append(ctx.author)
            await ctx.send(f"{ctx.author.display_name} se ha unido al equipo azul")
            if self.blue_boss is None:
                await self.new_blue_boss(ctx, ctx.author)


    @commands.guild_only()
    @commands.command(aliases=["jefe"])
    async def boss(self, ctx):
        if ctx.author not in self.players:
            return await ctx.send("No estás en la partida.")
        if ctx.author in self.red_team:
            await self.new_red_boss(ctx, ctx.author)
        if ctx.author in self.blue_team:
            await self.new_blue_boss(ctx, ctx.author)


    @commands.guild_only()
    @commands.command(aliases=["salir"])
    async def leave(self, ctx):
        if ctx.author not in self.players:
            return await ctx.send("No estás en la partida.")
        if ctx.author in self.red_team:
            self.red_team.remove(ctx.author)
        if ctx.author in self.blue_team:
            self.blue_team.remove(ctx.author)
        if self.red_boss == ctx.author:
            new_boss = choice(self.red_team) if self.red_team else None
            await self.new_red_boss(ctx, new_boss)
        if self.blue_boss == ctx.author:
            new_boss = choice(self.blue_team) if self.blue_team else None
            await self.new_blue_boss(ctx, new_boss)
        self.players.remove(ctx.author)
        await ctx.send(f"{ctx.author.display_name} ha abandonado la partida.")
    

    @commands.guild_only()
    @commands.command(aliases=["jugadores"])
    async def players(self, ctx):
        blue_team = ", ".join("{0}{1}{0}".format("**" if player == self.blue_boss else "", player.display_name) for player in self.blue_team)
        red_team = ", ".join("{0}{1}{0}".format("**" if player == self.red_boss else "", player.display_name) for player in self.red_team)
        if not red_team:
            red_team = "-"
        if not blue_team:
            blue_team = "-"
        return await ctx.send("Equipo azul: {}\nEquipo rojo: {}".format(blue_team, red_team))


    @commands.guild_only()
    @commands.command(aliases=["detener"])
    async def stop(self, ctx):
        if self.started:
            self.stopping = True
        self.started = False


    # @commands.guild_only()
    # @commands.command(aliases=["revelar"])
    # async def reveal(self, ctx, codename : str):
    #     if ctx.author != self.red_boss and ctx.author != self.blue_boss:
    #         return await ctx.send("No eres un jefe de espías")
    #     if ctx.author == self.blue_boss and self.turn != 1:
    #         return await ctx.send("No es tu turno.")
    #     if ctx.author == self.red_boss and self.turn != 2:
    #         return await ctx.send("No es tu turno.")
    #     codename = codename.strip().lower()
    #     try:
    #         codename_index = self.codenames.index(codename)
    #     except ValueError:
    #         return await ctx.send("Ese código no es válido")

    #     if self.revealed[codename_index]:
    #         return await ctx.send("Ese código ya ha sido revelado")

    #     self.revealed[codename_index] = True

    #     return await ctx.send(self.format_board())




    @commands.guild_only()    
    @commands.command(aliases=["empezar"])
    async def start(self, ctx):
        if self.started:
            return await ctx.send("¡El juego ya empezó!")
        if len(self.blue_team) < 2:
            return await ctx.send("No hay suficientes jugadores en el equipo azul para empezar el juego!")
        if len(self.red_team) < 2:
            return await ctx.send("No hay suficientes jugadores en el equipo rojo para empezar el juego!")
        self.codenames = sample(self.wordlist, 25)
        self.revealed = [False] * 25
        self.board = choice(self.boards)
        for i in range(choice([0, 1, 2, 3])):
            self.rotate_board()
        self.blue_agents = len([x for x in self.board if x == 1])
        self.red_agents = len([x for x in self.board if x == 2])
        if self.blue_agents < self.red_agents:
            self.turn = 2
        else:
            self.turn = 1

        boss_board_image = self.draw_board(boss=True)
        board_image = self.draw_board()
        try:
            boss_board_image.save("boss_board.png")
            board_image.save("board.png")
        except IOError:
            return await ctx.send("No se pudo crear la imagen del mapa")
        await self.blue_boss.send(file=discord.File("boss_board.png"))
        await self.red_boss.send(file=discord.File("boss_board.png"))
        await ctx.send(file=discord.File("board.png"))
        self.started = True
        self.stopping = False
        # await ctx.send("El juego ha empezado!")
        # board_message = await ctx.send(self.format_board())
        while not self.stopping:
            await self.round(ctx, board_image)
        await ctx.send("El juego ha finalizado!")
        self.players = []
        self.red_team = []
        self.blue_team = []
        self.revealed = [False] * 25
        self.red_boss = None
        self.blue_boss = None
        self.started = False
        self.stopping = False


    async def round(self, ctx, board_image):
        if self.turn == 1:
            boss = self.blue_boss
            team = self.blue_team
        else:
            boss = self.red_boss
            team = self.red_team

        await ctx.send(f"{boss.display_name}, dí una palabra y un número")


        def is_valid_clue(message):
            if message.channel != ctx.channel or message.author != boss:
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
            if clue in self.codenames and not self.revealed[self.codenames.index(clue)]:
                return False
            return True
        
        message = await self.bot.wait_for('message', check=is_valid_clue)
        await message.add_reaction("✅")

        _, amount = message.content.split()
        try:
            amount = int(amount)
            if amount == 0:
                amount = -1
        except ValueError:
            amount = -1

        def is_valid_codename(message):
            if message.channel != ctx.channel or message.author not in team:
                return False
            if message.author == boss:
                return False
            answer = message.content.strip().lower()
            if answer == "pasar turno":
                return True
            if answer not in self.codenames:
                return False
            if self.revealed[self.codenames.index(answer)]:
                return False
            return True

        await ctx.send("Ahora tu equipo debe encontrar tus espías.")
        codename = None
        while codename is None:
            message = await self.bot.wait_for('message', check=is_valid_codename)
            codename = message.content.strip().lower()
            if codename == "pasar turno":
                await ctx.send("Tienes que adivinar al menos una palabra")
                codename = None
        
        await message.add_reaction("✅")

        codename_index = self.codenames.index(codename)
        self.revealed[codename_index] = True
        codename_type = self.board[codename_index]
        if codename_type == 0:
            await ctx.send(f"{codename} es un civil")
        elif codename_type == 1:
            self.blue_agents -= 1
            await ctx.send(f"{codename} es un agente azul")
        elif codename_type == 2:
            self.red_agents -= 1
            await ctx.send(f"{codename} es un agente rojo")
        elif codename_type == 3:
            await ctx.send(f"{codename} es un asesino!")
            self.stopping = True
        else:
            await ctx.send(f"{codename} es de tipo {codename_type} (BUG)")


        self.reveal_type(board_image, codename_index)
        try:
            board_image.save("board.png")
        except IOError:
            await ctx.send("No se pudo crear la imagen del mapa")

        await ctx.send(file=discord.File("board.png"))

        if self.blue_agents == 0 or self.red_agents == 0:
            self.stopping = True

        if codename_type == self.turn and not self.stopping:
            await ctx.send("Puedes continuar adivinando o 'pasar turno'")

        while codename_type == self.turn and amount != 0 and not self.stopping:
            message = await self.bot.wait_for('message', check=is_valid_codename)
            await message.add_reaction("✅")
            codename = message.content.strip().lower()
            if codename == "pasar turno":
                break
            codename_index = self.codenames.index(codename)
            self.revealed[codename_index] = True
            codename_type = self.board[codename_index]
            if codename_type == 0:
                await ctx.send(f"{codename} es un civil")
            elif codename_type == 1:
                self.blue_agents -= 1
                await ctx.send(f"{codename} es un agente azul")
            elif codename_type == 2:
                self.red_agents -= 1
                await ctx.send(f"{codename} es un agente rojo")
            elif codename_type == 3:
                await ctx.send(f"{codename} es un asesino!")
                self.stopping = True
            else:
                await ctx.send(f"{codename} es de tipo {codename_type} (BUG)")

            self.reveal_type(board_image, codename_index)
            try:
                board_image.save("board.png")
            except IOError:
                await ctx.send("No se pudo crear la imagen del mapa")

            await ctx.send(file=discord.File("board.png"))

            amount -= 1

            if self.blue_agents == 0 or self.red_agents == 0:
                self.stopping = True

        if self.turn == 1:
            self.turn = 2
        else:
            self.turn = 1





def setup(bot):
    bot.add_cog(GameCog(bot))
