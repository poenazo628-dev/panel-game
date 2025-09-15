import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import gspread
import traceback

# --- 画像とスプレッドシートの設定 ---
ROUND_IMAGES = [
    'tabetabe1.png', 'tabetabe2.png', 'tabetabe3.png',
    'tabetabe4.png', 'tabetabe5.png', 'tabetabe6.png',
    'tabetabe7.png', 'tabetabe8.png', 'tabetabe9.png'
]
SPREADSHEET_NAME = 'tabetabe-panel'
# ------------------------------------

app = Flask(__name__)
CORS(app)

# --- スプレッドシートへの接続 ---
try:
    creds_json_str = os.environ.get('GSPREAD_CREDENTIALS')
    creds_json = json.loads(creds_json_str)
    gc = gspread.service_account_from_dict(creds_json)
    spreadsheet = gc.open(SPREADSHEET_NAME)
    print("スプレッドシートへの接続に成功しました。")
except Exception as e:
    print(f"スプレッドシートへの接続に失敗しました: {e}")
    spreadsheet = None
# ------------------------------------

# --- APIエンドポイント ---

@app.route('/get_status')
def get_status():
    player_id = request.args.get('player', 'Player1')
    print(f"\n--- /get_status が呼び出されました (Player: {player_id}) ---")

    if not spreadsheet:
        return jsonify({"status": "error", "message": "Spreadsheet not connected"}), 500

    try:
        print("1. プレイヤーIDを決定:", player_id)
        admin_sheet = spreadsheet.worksheet('AdminControl')
        print("2. 'AdminControl'シートを取得成功。")
        
        cell_value = admin_sheet.cell(1, 2).value
        print("3. B1セルの値を取得:", f"'{cell_value}'")

        current_round = int(cell_value) if cell_value and cell_value.isdigit() else 0
        print("4. ラウンド番号を決定:", current_round)

        if current_round == 0:
            print("--- /get_status 成功 (ラウンド0) ---")
            return jsonify({"status": "success", "round": 0})

        n = current_round + 1
        
        safe_round_index = max(0, min(current_round - 1, len(ROUND_IMAGES) - 1))
        background_image = ROUND_IMAGES[safe_round_index]
        print("5. 背景画像を決定:", background_image)

        sheet_to_fetch = 'Player1' if player_id == 'Admin' else player_id

        player_sheet = spreadsheet.worksheet(sheet_to_fetch)
        print(f"6. '{sheet_to_fetch}'シートを取得成功。")

        cell_range = f'A1:{gspread.utils.rowcol_to_a1(n, n)}'
        panel_data = player_sheet.get(cell_range)
        print(f"7. '{sheet_to_fetch}'シートから範囲 '{cell_range}' のデータを取得。")

        print("--- /get_status 成功 ---")
        return jsonify({
            "status": "success", "round": current_round, "n": n,
            "panels": panel_data, "backgroundImage": background_image
        })
    except Exception as e:
        print(f"!!! /get_statusでエラー発生: {e} !!!")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

# (他のAPI関数 ... /open_panel, /admin_open_panel)
@app.route('/open_panel', methods=['POST'])
def open_panel():
    data = request.json
    user_id = data.get('user', 'Player1')
    row = data.get('row')
    col = data.get('col')
    print(f"--- パネル開放リクエスト --- Player: '{user_id}', Cell: ({row}, {col})")
    try:
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '1')
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! open_panelエラー: {e} !!!")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin_open_panel', methods=['POST'])
def admin_open_panel():
    data = request.json
    user_id = data.get('user', 'Player1')
    row = data.get('row')
    col = data.get('col')
    print(f"--- 管理者パネル開放 --- Player: '{user_id}', Cell: ({row}, {col})")
    try:
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '2')
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! admin_open_panelエラー: {e} !!!")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/next_round', methods=['POST'])
def next_round():
    print("\n--- /next_round が呼び出されました ---")
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        new_round = min(current_round + 1, 9)
        admin_sheet.update_cell(1, 2, str(new_round))
        print(f"1. ラウンドを {new_round} に更新しました。")

        presets_sheet = spreadsheet.worksheet('AdminPresets')
        n = new_round + 1
        
        start_col = 1
        if new_round > 1:
            start_col = sum(range(2, new_round + 1))

        end_col = start_col + n - 1
        preset_range = f'{gspread.utils.rowcol_to_a1(2, start_col)}:{gspread.utils.rowcol_to_a1(n + 1, end_col)}'
        print(f"2. AdminPresetsから範囲 '{preset_range}' を読み取ります。")
        preset_data = presets_sheet.get(preset_range)

        for i in range(1, 9):
            player_id = f'Player{i}'
            player_sheet = spreadsheet.worksheet(player_id)
            
            # --- ▼▼▼ より確実なリセット処理に変更 ▼▼▼ ---
            # 1. まず、最大範囲(10x10)を空のセルで埋めて完全にクリアする
            max_size = 10
            max_range = f'A1:{gspread.utils.rowcol_to_a1(max_size, max_size)}'
            empty_board_data = [[''] * max_size for _ in range(max_size)]
            player_sheet.update(max_range, empty_board_data)
            print(f"中間報告: '{player_id}'シートを完全にクリアしました。")

            # 2. その後、新しいラウンドのプリセットデータを書き込む
            update_cells = []
            for r, row_data in enumerate(preset_data):
                for c, cell_value in enumerate(row_data):
                    if c < len(row_data):
                        cell = gspread.Cell(row=r+1, col=c+1, value='2' if str(cell_value) == '1' else '0')
                        update_cells.append(cell)
            if update_cells:
                player_sheet.update_cells(update_cells, value_input_option='RAW')
            # --- ▲▲▲ ここまで変更 ▲▲▲ ---

            print(f"3. '{player_id}'シートをプリセットで更新しました。")
        
        return jsonify({"status": "success", "new_round": new_round})
    except Exception as e:
        print(f"!!! /next_roundでエラー発生: {e} !!!")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/calculate_scores', methods=['GET'])
def calculate_scores():
    print("\n--- /calculate_scores が呼び出されました ---")
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        n = current_round + 1
        total_panels = n * n
        
        results = []
        for i in range(1, 9):
            player_id = f'Player{i}'
            player_sheet = spreadsheet.worksheet(player_id)
            all_values = player_sheet.get(f'A1:{gspread.utils.rowcol_to_a1(n, n)}')
            opened_count = 0
            for row in all_values:
                for cell in row:
                    if cell == '1' or cell == '2':
                        opened_count += 1
            
            unopened_count = total_panels - opened_count
            score = abs(unopened_count - opened_count)
            results.append({"player": player_id, "score": score, "opened": opened_count})

        # --- ▼▼▼ ここを修正 ▼▼▼ ---
        # スコアの降順（大きい順）に並べ替える
        results.sort(key=lambda x: x['score'], reverse=True)
        # --- ▲▲▲ ここまで修正 ▲▲▲ ---
        
        results_sheet = spreadsheet.worksheet('Results')
        results_sheet.append_row([f"Round {current_round} Results"])
        for res in results:
            results_sheet.append_row([res['player'], res['score'], res['opened']])

        return jsonify({"status": "success", "results": results})
    except Exception as e:
        print(f"!!! /calculate_scoresでエラー発生: {e} !!!")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/reset_game', methods=['POST'])
def reset_game():
    print("\n--- /reset_game が呼び出されました ---")
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        admin_sheet.update_cell(1, 2, '0')
        print("1. ラウンドを0にリセットしました。")

        for i in range(1, 9):
            player_sheet = spreadsheet.worksheet(f'Player{i}')
            player_sheet.clear()
            print(f"2. Player{i}シートをクリアしました。")
        
        results_sheet = spreadsheet.worksheet('Results')
        results_sheet.clear()
        print("3. Resultsシートをクリアしました。")

        return jsonify({"status": "success", "message": "ゲームがリセットされました。"})
    except Exception as e:
        print(f"!!! /reset_gameでエラー発生: {e} !!!")
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

