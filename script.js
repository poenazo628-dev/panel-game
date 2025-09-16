// --- グローバル変数 ---
// Renderで公開したサーバーのURLをここに貼り付ける
const API_BASE_URL = 'https://panel-game-server.onrender.com';
let myPlayerId = 'Player1'; // デフォルト値

// --- サーバーのスリープを防ぐ機能 ---
function keepServerAwake() {
    fetch(`${API_BASE_URL}/get_status?player=ping`)
        .then(response => {
            if (!response.ok) {
                console.warn('サーバーのPingに失敗しました。');
            }
        })
        .catch(error => {
            console.error('サーバーへのPing接続エラー:', error);
        });
}
// 30秒ごとにサーバーを起こし続ける
setInterval(keepServerAwake, 30000);


// --- ページの読み込みが完了したときの処理 ---
window.onload = function() {
    // URLからプレイヤーIDを取得
    const params = new URLSearchParams(window.location.search);
    const player = params.get('player');
    if (player) {
        myPlayerId = player;
    }
    console.log(`ページが読み込まれました。${myPlayerId}としてゲームを初期化します。`);
    
    initializeGame();
    setupAdminControls();
    keepServerAwake(); // ページ読み込み直後にも一度実行
};


// --- ゲームの初期化 ---
async function initializeGame() {
    try {
        const response = await fetch(`${API_BASE_URL}/get_status?player=${myPlayerId}`);
        if (!response.ok) {
            throw new Error(`Server responded with status ${response.status}`);
        }
        const data = await response.json();

        if (data.status === 'success') {
            if (data.round === 0) {
                showStandbyScreen();
            } else if (data.round === 'clear') {
                showGameClearScreen();
            } else {
                const { round, n, panels, backgroundImage } = data;
                document.getElementById('info-display').textContent = `ラウンド ${round} (${n}x${n})`;
                document.getElementById('score-container').style.display = 'none';
                document.getElementById('game-board').style.display = 'grid';
                console.log(`[ブラウザ側の確認] 背景画像として'${backgroundImage}'を設定しようとしています。`);
                createGrid(n, panels, backgroundImage);
            }
        } else {
            document.getElementById('info-display').textContent = 'エラー: ゲーム情報の取得に失敗しました。';
        }
    } catch (error) {
        console.error('初期化エラー:', error);
        document.getElementById('info-display').textContent = `エラー: ${error.message}`;
    }
}

// --- 待機画面の表示 ---
function showStandbyScreen() {
    document.getElementById('game-board').style.display = 'none';
    document.getElementById('score-container').style.display = 'none';
    document.getElementById('info-display').textContent = 'ゲーム開始待機中...';
}

// --- ゲームクリア画面の表示 ---
async function showGameClearScreen() {
    document.getElementById('game-board').style.display = 'none';
    document.getElementById('info-display').textContent = 'ゲームクリア！お疲れ様でした！最終結果を集計中...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/get_final_scores`);
        const data = await response.json();
        if (data.status === 'success') {
            displayScores(data.results, true); // trueは最終結果であることを示す
        } else {
            document.getElementById('info-display').textContent = '最終結果の取得に失敗しました。';
        }
    } catch (error) {
        console.error('最終結果取得エラー:', error);
        document.getElementById('info-display').textContent = '最終結果の取得中にエラーが発生しました。';
    }
}


// --- ゲーム盤の生成 ---
function createGrid(n, panels, backgroundImage) {
    const gameBoard = document.getElementById('game-board');
    gameBoard.innerHTML = '';
    gameBoard.style.setProperty('--n', n);
    gameBoard.style.backgroundImage = `url('${backgroundImage}')`;

    for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
            const panel = document.createElement('div');
            panel.classList.add('panel');
            if (panels[r] && (panels[r][c] === '1' || panels[r][c] === '2')) {
                panel.classList.add('is-hidden');
            }

            panel.addEventListener('click', async () => {
                if (panel.classList.contains('is-hidden')) return;

                const isAdminMode = document.getElementById('admin-mode-checkbox')?.checked;
                const endpoint = isAdminMode ? '/admin_open_panel' : '/open_panel';
                const bodyPayload = {
                    user: myPlayerId,
                    row: r + 1,
                    col: c + 1,
                };

                // --- [バグ修正] データの不整合を完全に防ぐロジック ---
                // 1. 先に見た目を変える
                panel.classList.add('is-hidden');

                try {
                    // 2. サーバーに書き込みを依頼
                    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(bodyPayload),
                    });
                    
                    const result = await response.json();

                    // 3. もしサーバーが失敗したら、見た目を元に戻す
                    if (!response.ok || result.status !== 'success') {
                        console.error('サーバーへの書き込みに失敗しました。パネルを元に戻します。', result);
                        panel.classList.remove('is-hidden');
                        alert('サーバーとの通信に失敗しました。もう一度お試しください。');
                    }
                } catch (error) {
                    // 4. 通信自体が失敗した場合も、見た目を元に戻す
                    console.error('通信エラー:', error);
                    panel.classList.remove('is-hidden');
                    alert('サーバーとの通信に失敗しました。もう一度お試しください。');
                }
                // ----------------------------------------------------
            });
            gameBoard.appendChild(panel);
        }
    }
}


// --- スコア表示 ---
function displayScores(results, isFinal = false) {
    const scoreContainer = document.getElementById('score-container');
    const infoDisplay = document.getElementById('info-display');
    
    document.getElementById('game-board').style.display = 'none';
    scoreContainer.style.display = 'block';
    
    const titleText = isFinal ? '最終結果' : `ラウンド${results.round} 結果`;
    infoDisplay.textContent = titleText;

    let tableHTML = '<table><tr><th>順位</th><th>プレイヤー</th><th>スコア</th><th>開いた枚数</th></tr>';
    results.forEach((result, index) => {
        tableHTML += `<tr>
            <td>${index + 1}</td>
            <td>${result.player}</td>
            <td>${result.score}</td>
            <td>${result.opened}</td>
        </tr>`;
    });
    tableHTML += '</table>';
    scoreContainer.innerHTML = tableHTML;

    // 管理者の場合、スコア画面に「次のラウンドへ」ボタンを追加
    if (myPlayerId === 'Admin' && !isFinal) {
        const nextRoundBtn = document.createElement('button');
        nextRoundBtn.textContent = '次のラウンドへ';
        nextRoundBtn.onclick = () => {
            fetch(`${API_BASE_URL}/next_round`, { method: 'POST' })
                .then(() => window.location.reload());
        };
        scoreContainer.appendChild(nextRoundBtn);
    }
}


// --- 管理者コントロール ---
function setupAdminControls() {
    const adminPanel = document.getElementById('admin-panel');
    if (myPlayerId === 'Admin') {
        adminPanel.style.display = 'flex';

        const nextRoundBtn = document.getElementById('next-round-button');
        if (nextRoundBtn) {
            nextRoundBtn.onclick = () => {
                fetch(`${API_BASE_URL}/next_round`, { method: 'POST' })
                    .then(() => window.location.reload());
            };
        }
        
        const calcScoreBtn = document.getElementById('calc-score-button');
        if (calcScoreBtn) {
            calcScoreBtn.onclick = async () => {
                try {
                    const response = await fetch(`${API_BASE_URL}/calculate_scores`);
                    const data = await response.json();
                    if (data.status === 'success') {
                        displayScores(data.results);
                    } else {
                        alert('スコア計算に失敗しました。');
                    }
                } catch (error) {
                    console.error('スコア計算エラー:', error);
                    alert('スコア計算中にエラーが発生しました。');
                }
            };
        }

        const resetBtn = document.getElementById('reset-button');
        if (resetBtn) {
            resetBtn.onclick = () => {
                fetch(`${API_BASE_URL}/reset_game`, { method: 'POST' })
                    .then(() => window.location.reload());
            };
        }
    } else {
        adminPanel.style.display = 'none';
    }
}

