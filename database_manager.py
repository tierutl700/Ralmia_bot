import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path="game_records.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # デッキテーブル作成（シンプル化）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_name TEXT UNIQUE NOT NULL
        )
        ''')
        
        # 対戦記録テーブル作成
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            player_name TEXT NOT NULL,
            player_id TEXT NOT NULL,
            result TEXT NOT NULL,
            my_deck TEXT NOT NULL,
            opponent_deck TEXT NOT NULL,
            turn_order TEXT NOT NULL,
            memo TEXT
        )
        ''')
        
        # サンプルデッキデータを挿入（まだデータがない場合のみ）
        cursor.execute('SELECT COUNT(*) FROM decks')
        if cursor.fetchone()[0] == 0:
            sample_decks = [
                ('アグロデッキ',),
                ('コントロールデッキ',),
                ('ミッドレンジデッキ',),
                ('コンボデッキ',)
            ]
            cursor.executemany(
                'INSERT INTO decks (deck_name) VALUES (?)',
                sample_decks
            )
        
        conn.commit()
        conn.close()
    
    def get_deck_list(self) -> List[str]:
        """デッキリストを取得（デッキ名のみ）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT deck_name FROM decks ORDER BY deck_name')
        rows = cursor.fetchall()
        
        deck_list = [row[0] for row in rows]
        
        conn.close()
        return deck_list
    
    def add_record(self, user_name: str, user_id: int, result: str, my_deck: str, opponent_deck: str, turn_order: str, memo: str = "") -> bool:
        """対戦記録を追加"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
            INSERT INTO game_records (timestamp, player_name, player_id, result, my_deck, opponent_deck, turn_order, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, user_name, str(user_id), result, my_deck, opponent_deck, turn_order, memo))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"記録追加エラー: {e}")
            return False
    
    def get_user_stats(self, user_id: Optional[int] = None) -> Dict:
        """ユーザーの統計を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('SELECT result FROM game_records WHERE player_id = ?', (str(user_id),))
        else:
            cursor.execute('SELECT result FROM game_records')
        
        results = cursor.fetchall()
        
        wins = sum(1 for result in results if result[0] == '勝ち')
        losses = sum(1 for result in results if result[0] == '負け')
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        conn.close()
        
        return {
            'wins': wins,
            'losses': losses,
            'total': total,
            'win_rate': win_rate
        }

    
    def add_deck(self, deck_name: str) -> bool:
        deck_name = deck_name.strip()
        if not deck_name:
            print("空のデッキ名が入力されました")
            return False

        try:
            with sqlite3.connect(self.db_path, check_same_thread=False, timeout=10) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO decks (deck_name) VALUES (?)", (deck_name,))
                conn.commit()
            print(f"デッキ追加成功: {deck_name}")
            return True
        except sqlite3.IntegrityError as e:
            print(f"重複エラー（IntegrityError）: {e}")
            return False
        except sqlite3.OperationalError as e:
            print(f"OperationalError: {e}")  # ロックなど
            return False
        except Exception as e:
            print(f"不明なエラー: {e}")
            return False
            
            
    def delete_deck(self, deck_name: str) -> bool:
        """デッキを削除"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM decks WHERE deck_name = ?', (deck_name,))
            deleted_rows = cursor.rowcount
            
            conn.commit()
            conn.close()
            return deleted_rows > 0
        except Exception as e:
            print(f"デッキ削除エラー: {e}")
            return False
    
    def reset_records(self) -> bool:
        """対戦記録をリセット"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM game_records')
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"記録リセットエラー: {e}")
            return False
    
    def get_recent_records(self, limit: int = 10) -> List[Dict]:
        """最近の対戦記録を取得"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT timestamp, player_name, result, my_deck, opponent_deck, turn_order
        FROM game_records
        ORDER BY timestamp DESC
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        
        records = []
        for row in rows:
            records.append({
                '日時': row[0],
                'プレイヤー': row[1],
                '勝敗': row[2],
                '自分デッキ': row[3],
                '相手デッキ': row[4],
                '先攻後攻': row[5]
            })
        
        conn.close()
        return records
