// --- 設定 ---
const API_BASE_URL = 'https://panel-game-server.onrender.com'; 
// ------------------------------------

let myPlayerId = 'Player1';

// --- [新機能] サーバーをスリープさせないためのPing機能 ---
function keepServerAwake() {
    fetch(`${API_BASE_URL}/get_status?player=ping`) // サーバーに簡単なリクエストを送る
        .then(res => {
            if (res.ok) {
                console.log("サーバーは起動中です。");
            } else {
                console.warn("サーバーのPingに失敗しました。");
            }
        })
        .catch(err => {
            console.error("サーバーへの接続が失われました:", err);
        });
}

// 30秒ごとにサーバーを起こし続ける
setInterval(keepServerAwake, 30000); 
// ----------------------------------------------------


window.onload = function() {
    const params = new URLSearchParams(window.location.search);
    const player = params.get('player');
    if (player) {
        myPlayerId = player;
    }
    console.log(`ページが読み込まれました。${myPlayerId}としてゲームを初期化します。`);
    initializeGame();
};

async function initializeGame() {
    const infoDisplay = document.getElementById('info-display');
    const gameBoard = document.getElementById('game-board');
    const scoreContainer = document.getElementById('score-container');

    gameBoard.style.display = 'grid';
    if(scoreContainer) scoreContainer.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/get_status?player=${myPlayerId}`);
        if (!response.ok) throw new Error(`Server responded with status ${response.status}`);
        const data = await response.json();

        if (data.status === 'success') {
            if (data.round === 0) {
                infoDisplay.textContent = 'ゲーム開始待機中...';
                gameBoard.style.display = 'none';
            } else if (data.round === 'clear') {
                infoDisplay.textContent = 'ゲームクリア！お疲れ様でした！';
                gameBoard.style.display = 'none';
            } else {
                const { round, n, panels, backgroundImage } = data;
                infoDisplay.textContent = `ラウンド ${round} (${n}x${n})`;
                if (backgroundImage) {
                    console.log(`[ブラウザ側の確認] 背景画像として'${backgroundImage}'を設定しようとしています。`);
                    gameBoard.style.backgroundImage = `url('${backgroundImage}')`;
                }
                createGrid(n, panels);
            }
        } else {
            throw new Error(data.message || 'ゲーム情報の取得に失敗しました。');
        }
    } catch (error) {
        console.error('初期化エラー:', error);
        infoDisplay.textContent = `エラー: ${error.message}`;
        gameBoard.style.display = 'none';
    }
    setupAdminControls();
}

function createGrid(n, panels) {
    const gameBoard = document.getElementById('game-board');
    gameBoard.innerHTML = '';
    gameBoard.style.setProperty('--n', n);

    if (!panels || panels.length === 0) return;

    for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
            const panel = document.createElement('div');
            panel.classList.add('panel');
            if (panels[r] && (panels[r][c] === '1' || panels[r][c] === '2')) {
                panel.classList.add('is-hidden');
            }
            panel.addEventListener('click', () => handlePanelClick(panel, r, c));
            gameBoard.appendChild(panel);
        }
    }
}

async function handlePanelClick(panel, r, c) {
    if (panel.classList.contains('is-hidden')) return;
    
    const isAdminMode = document.getElementById('admin-mode-checkbox')?.checked;
    if (myPlayerId === 'Admin' && !isAdminMode) return;

    panel.classList.add('is-hidden');
    
    const endpoint = (myPlayerId === 'Admin' && isAdminMode) ? '/admin_open_panel' : '/open_panel';
    
    try {
        await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: myPlayerId, row: r + 1, col: c + 1 }),
        });
    } catch (error) {
        console.error('パネルクリック通信エラー:', error);
        panel.classList.remove('is-hidden');
    }
}

function setupAdminControls() {
    const adminPanel = document.getElementById('admin-panel');
    if (myPlayerId !== 'Admin' || !adminPanel) {
        if(adminPanel) adminPanel.style.display = 'none';
        return;
    }
    
    adminPanel.style.display = 'flex';

    const nextRoundBtn = document.getElementById('next-round-button');
    const calcScoreBtn = document.getElementById('calc-score-button');
    const resetBtn = document.getElementById('reset-game-button');

    if (nextRoundBtn) {
        nextRoundBtn.onclick = async () => {
            await fetch(`${API_BASE_URL}/next_round`, { method: 'POST' });
            window.location.reload();
        };
    }
    if (calcScoreBtn) {
        calcScoreBtn.onclick = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/calculate_scores`);
                const data = await response.json();
                if (data.status === 'success') {
                    displayScores(data.results);
                } else {
                    console.error("スコア計算APIエラー:", data.message);
                }
            } catch (error) {
                console.error("スコア計算fetchエラー:", error);
            }
        };
    }
    if (resetBtn) {
        resetBtn.onclick = async () => {
            await fetch(`${API_BASE_URL}/reset_game`, { method: 'POST' });
            window.location.reload();
        };
    }
}

function displayScores(results) {
    const gameBoard = document.getElementById('game-board');
    const scoreContainer = document.getElementById('score-container');
    const adminPanel = document.getElementById('admin-panel');

    if (gameBoard) gameBoard.style.display = 'none';
    if (adminPanel) adminPanel.style.display = 'none';
    if (scoreContainer) {
        scoreContainer.style.display = 'block';
        scoreContainer.innerHTML = '<h2>スコアランキング</h2>';

        const table = document.createElement('table');
        table.innerHTML = `<thead><tr><th>順位</th><th>プレイヤー</th><th>スコア</th><th>開いた枚数</th></tr></thead>`;
        const tbody = document.createElement('tbody');
        results.forEach((res, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${index + 1}</td><td>${res.player}</td><td>${res.score}</td><td>${res.opened}</td>`;
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        scoreContainer.appendChild(table);

        if (myPlayerId === 'Admin') {
            const nextRoundBtn = document.createElement('button');
            nextRoundBtn.textContent = '次のラウンドへ';
            nextRoundBtn.onclick = async () => {
                await fetch(`${API_BASE_URL}/next_round`, { method: 'POST' });
                window.location.reload();
            };
            scoreContainer.appendChild(nextRoundBtn);
        }
    }
}

