// ▼▼▼▼▼【最終ステップで書き換える場所】▼▼▼▼▼
// Renderで公開したサーバーのURLをここに貼り付ける
const API_BASE_URL = 'https://panel-game-server.onrender.com'; 
// ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

// URLから自分のプレイヤーIDを取得する
const urlParams = new URLSearchParams(window.location.search);
const myPlayerId = urlParams.get('player') || 'Player1';

// ページの読み込みが完了したら実行する
window.onload = function() {
    console.log(`ページが読み込まれました。${myPlayerId}としてゲームを初期化します。`);

    const controlsPanel = document.getElementById('controls');
    if (myPlayerId.toLowerCase() !== 'admin') {
        controlsPanel.style.display = 'none';
    }

    const nextRoundButton = document.getElementById('next-round-button');
    if (nextRoundButton) {
        nextRoundButton.addEventListener('click', () => {
            fetch(`${API_BASE_URL}/next_round`, { method: 'POST' })
                .then(() => {
                    window.location.reload();
                });
        });
    }

    const calculateScoreButton = document.getElementById('calculate-score-button');
    if (calculateScoreButton) {
        calculateScoreButton.addEventListener('click', async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/calculate_scores`);
                const data = await response.json();
                if (data.status === 'success') {
                    displayScores(data.results);
                } else {
                    alert('スコアの計算に失敗しました。');
                }
            } catch (error) {
                console.error('スコア計算通信エラー:', error);
                alert('サーバーとの通信に失敗しました。');
            }
        });
    }

    initializeGame();
};

// ... (これ以降の関数の内容は前回から変更ありません) ...

async function initializeGame() {
    try {
        const boardOwner = myPlayerId.toLowerCase() === 'admin' ? 'Player1' : myPlayerId;
        const response = await fetch(`${API_BASE_URL}/get_status?player=${boardOwner}`);
        
        const data = await response.json();
        if (data.status === 'success') {
            const { round, n, panels } = data;
            if (myPlayerId.toLowerCase() === 'admin') {
                document.getElementById('info-display').textContent = `【管理者モード】 | ラウンド ${round} (${n}x${n})`;
            } else {
                document.getElementById('info-display').textContent = `あなたは ${myPlayerId} です | ラウンド ${round} (${n}x${n})`;
            }
            createGrid(n, panels);
        } else {
            document.getElementById('info-display').textContent = 'エラー: ゲーム情報の取得に失敗しました。';
        }
    } catch (error) {
        console.error('通信エラー:', error);
        document.getElementById('info-display').textContent = 'エラー: サーバーに接続できません。';
    }
}

function displayScores(results) {
    const gameBoard = document.getElementById('game-board');
    const scoreboardContainer = document.getElementById('scoreboard-container');

    gameBoard.style.display = 'none';
    scoreboardContainer.innerHTML = '';

    results.sort((a, b) => b.score - a.score);

    const table = document.createElement('table');
    table.innerHTML = `
        <thead>
            <tr>
                <th>順位</th>
                <th>プレイヤー</th>
                <th>スコア</th>
                <th>開いた枚数</th>
                <th>閉じた枚数</th>
            </tr>
        </thead>
        <tbody>
        </tbody>
    `;

    const tbody = table.querySelector('tbody');
    results.forEach((result, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${index + 1}位</td>
            <td>${result.player}</td>
            <td>${result.score}</td>
            <td>${result.opened}</td>
            <td>${result.closed}</td>
        `;
        tbody.appendChild(row);
    });

    scoreboardContainer.appendChild(table);
}

function createGrid(n, panels) {
    const gameBoard = document.getElementById('game-board');
    const scoreboardContainer = document.getElementById('scoreboard-container');
    
    gameBoard.style.display = 'grid';
    scoreboardContainer.innerHTML = '';
    gameBoard.innerHTML = '';
    gameBoard.style.setProperty('--n', n);

    for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
            const panel = document.createElement('div');
            panel.classList.add('panel');
            if (r < panels.length && c < panels[r].length && (panels[r][c] === '1' || panels[r][c] === '2')) {
                panel.classList.add('is-hidden');
            }
            panel.addEventListener('click', async () => {
                if (panel.classList.contains('is-hidden')) return;

                const isAdminMode = document.getElementById('admin-mode-checkbox').checked;

                if (myPlayerId.toLowerCase() === 'admin' && !isAdminMode) {
                    console.log("管理者モードではないため、パネルは開きません。");
                    return; 
                }

                panel.classList.add('is-hidden');
                
                const endpoint = isAdminMode ? '/admin_open_panel' : '/open_panel';
                
                const targetPlayer = myPlayerId.toLowerCase() === 'admin' ? 'Player1' : myPlayerId;
                
                try {
                    await fetch(`${API_BASE_URL}${endpoint}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            user: targetPlayer,
                            row: r + 1,
                            col: c + 1,
                        }),
                    });
                } catch (error) {
                    console.error('通信エラー:', error);
                }
            });
            gameBoard.appendChild(panel);
        }
    }
}

