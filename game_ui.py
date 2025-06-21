
import discord
from discord.ui import Select, View, Button

class GameRecordView(View):
    def __init__(self, db_manager):
        super().__init__(timeout=300)
        self.db_manager = db_manager
        self.result = None
        self.my_deck = None
        self.opponent_deck = None
        self.turn_order = None
    
    @discord.ui.button(label="勝ち", style=discord.ButtonStyle.success, emoji="🏆")
    async def win_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "勝ち"
        await interaction.response.send_message("🏆 勝ちが選択されたよ！\n②自分のデッキを選択してね：", 
                                               view=DeckSelectView(self.db_manager, self, "my_deck"), ephemeral=True)

    @discord.ui.button(label="負け", style=discord.ButtonStyle.danger, emoji="💀")
    async def lose_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "負け"
        await interaction.response.send_message("💀 負けが選択されたよ！\n②自分のデッキを選択してね：", 
                                               view=DeckSelectView(self.db_manager, self, "my_deck"), ephemeral=True)

class DeckSelectView(View):
    def __init__(self, db_manager, parent_view, deck_type):
        super().__init__(timeout=300)
        self.db_manager = db_manager
        self.parent_view = parent_view
        self.deck_type = deck_type
        self.add_item(DeckSelect(db_manager, parent_view, deck_type))

class DeckSelect(Select):
    def __init__(self, db_manager, parent_view, deck_type):
        self.db_manager = db_manager
        self.parent_view = parent_view
        self.deck_type = deck_type
        
        # SQLiteからデッキリストを取得
        deck_list = db_manager.get_deck_list()
        
        options = []
        for deck_name in deck_list:
            options.append(discord.SelectOption(
                label=deck_name,
                emoji="🎴",
                value=deck_name
            ))
        
        if not options:
            options = [discord.SelectOption(label="デッキが見つからなかったよ", value="none")]
            
        placeholder = "自分のデッキを選択..." if deck_type == "my_deck" else "相手のデッキを選択..."
        super().__init__(placeholder=placeholder, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.deck_type == "my_deck":
            self.parent_view.my_deck = self.values[0]
            await interaction.response.send_message(f"✅ 自分のデッキ: **{self.values[0]}**\n③相手のデッキを選択してね：", 
                                                   view=DeckSelectView(self.db_manager, self.parent_view, "opponent_deck"), ephemeral=True)
        elif self.deck_type == "opponent_deck":
            self.parent_view.opponent_deck = self.values[0]
            await interaction.response.send_message(f"✅ 相手のデッキ: **{self.values[0]}**\n④先攻・後攻を選択してね：", 
                                                   view=TurnOrderView(self.db_manager, self.parent_view), ephemeral=True)

class TurnOrderView(View):
    def __init__(self, db_manager, parent_view):
        super().__init__(timeout=300)
        self.db_manager = db_manager
        self.parent_view = parent_view

    @discord.ui.button(label="先攻", style=discord.ButtonStyle.primary, emoji="1️⃣")
    async def first_turn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent_view.turn_order = "先攻"
        await self.save_record(interaction)

    @discord.ui.button(label="後攻", style=discord.ButtonStyle.secondary, emoji="2️⃣")
    async def second_turn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent_view.turn_order = "後攻"
        await self.save_record(interaction)

    async def save_record(self, interaction):
        # SQLiteに記録を保存
        success = self.db_manager.add_record(
            user_name=interaction.user.display_name,
            user_id=interaction.user.id,
            result=self.parent_view.result,
            my_deck=self.parent_view.my_deck,
            opponent_deck=self.parent_view.opponent_deck,
            turn_order=self.parent_view.turn_order
        )
        
        if success:
            embed = discord.Embed(title="📝 対戦記録が保存されたよ！", color=0x00ff00)
            embed.add_field(name="勝敗", value=self.parent_view.result, inline=True)
            embed.add_field(name="自分のデッキ", value=self.parent_view.my_deck, inline=True)
            embed.add_field(name="相手のデッキ", value=self.parent_view.opponent_deck, inline=True)
            embed.add_field(name="先攻・後攻", value=self.parent_view.turn_order, inline=True)
            embed.set_footer(text="記録がSQLiteデータベースに保存されました")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ 記録の保存に失敗しました。管理者に連絡してください。", ephemeral=True)

class DeckManageView(View):
    def __init__(self, db_manager):
        super().__init__(timeout=300)
        self.db_manager = db_manager

    @discord.ui.button(label="新しいデッキを追加", style=discord.ButtonStyle.primary, emoji="➕")
    async def add_deck_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddDeckModal(self.db_manager))

    @discord.ui.button(label="デッキを削除", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_deck_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("削除するデッキを選択してください：", 
                                               view=DeleteDeckView(self.db_manager), ephemeral=True)

class DeleteDeckView(View):
    def __init__(self, db_manager):
        super().__init__(timeout=300)
        self.db_manager = db_manager
        self.add_item(DeleteDeckSelect(db_manager))

class DeleteDeckSelect(Select):
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
        # デッキリストを取得
        deck_list = db_manager.get_deck_list()
        
        options = []
        for deck_name in deck_list:
            options.append(discord.SelectOption(
                label=deck_name,
                emoji="🗑️",
                value=deck_name
            ))
        
        if not options:
            options = [discord.SelectOption(label="デッキが見つからなかったよ", value="none")]
        
        super().__init__(placeholder="削除するデッキを選択...", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            await interaction.response.send_message("削除できるデッキがないよ", ephemeral=True)
            return
        
        success = self.db_manager.delete_deck(self.values[0])
        
        if success:
            embed = discord.Embed(title="🗑️ デッキが削除されました", color=0xff0000)
            embed.add_field(name="削除されたデッキ", value=self.values[0], inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ デッキの削除に失敗しました", ephemeral=True)

class AddDeckModal(discord.ui.Modal, title="新しいデッキを追加"):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager

    deck_name = discord.ui.TextInput(label="デッキ名", placeholder="デッキの名前を入力...")

    async def on_submit(self, interaction: discord.Interaction):
        success = self.db_manager.add_deck(deck_name=self.deck_name.value)
        
        if success:
            embed = discord.Embed(title="✅ デッキが追加されました！", color=0x00ff00)
            embed.add_field(name="デッキ名", value=self.deck_name.value, inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ デッキの追加に失敗しました。同じ名前のデッキが既に存在する可能性があります。", ephemeral=True)

class ResetRecordsView(View):
    def __init__(self, db_manager):
        super().__init__(timeout=300)
        self.db_manager = db_manager

    @discord.ui.button(label="確認", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        success = self.db_manager.reset_records()
        
        if success:
            embed = discord.Embed(title="🗑️ 対戦記録をリセットしました", color=0xff0000)
            embed.add_field(name="結果", value="すべての対戦記録が削除されました", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ 記録のリセットに失敗しました。", ephemeral=True)

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("リセットをキャンセルしました。", ephemeral=True)
