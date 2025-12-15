# Network Programming HW3 – Game Store System

Tkinter clients for players/developers, a lobby server that coordinates rooms and launches games, plus a simple file server for zipping/unzipping uploaded game versions.

## Prerequisites
- Python 3.10+ (Tkinter included on most platforms)
- Run commands from repo root (`hw3`)
- Configure host/port in `player_client/config.json`, `dev_client/config.json`, and `server/lobby/config.json`. File server host/port is in `server/dev/config.json`.

## Start servers (on the host everyone can reach)
1) File server (handles zip upload/download):
   - `python -m server.dev.dev_server`
2) Lobby server (rooms, auth, game launch):
   - `python -m server.lobby.lobby`
   - Ensure firewall opens the lobby port and the game ports it will spawn.
3) Game servers are launched per-room by lobby; they bind the host/port passed from lobby. Use a reachable host (not 127.0.0.1) when running remotely.

## Developer workflow
1) Run GUI: `python -m dev_client.main_gui`
2) Register/Login.
3) Create Game (now supports immediate upload):
   - Fill name/description/max players.
   - Provide version (e.g., `1.0.0`), changelog, and select the game folder to upload.
   - The client zips the folder, calls `developer_create_version`, and uploads to the file server.
4) Later uploads: use “Upload New Version” from the library; version must bump above the latest.

## Player workflow
1) Run GUI: `python -m player_client.main_gui`
2) Register/Login.
3) Browse store, view game detail/ratings.
4) Join or create a room for a game, wait for enough players, host clicks Start.
5) When lobby broadcasts `game_start`, the client spawns the downloaded game (`python -m client.client ...`) inside the player’s game folder.

## Test games (local quick run)
- RPS: `python -m test_game.rps.server.server --host 0.0.0.0 --port 23456`
- TicTacToe: `python -m test_game.tic_tac_toe.server.server --host 0.0.0.0 --port 34567`
- Guess (multi): `python -m test_game.guess.server.server --host 0.0.0.0 --port 45678`
Clients: `python -m test_game.<game>.client.client --host <server_ip> --port <port> --user <name>`

## Notes
- Ratings: only logged-in players can submit; lobby should check play history via `player_sessions`.
- If clients can’t reach the game after lobby start, verify `game_host` uses a reachable IP and the game port is open.

## Game rules (built-in demos)
- Rock-Paper-Scissors: two players, first to score 3 wins. Each round both pick rock/paper/scissors; rock beats scissors, scissors beats paper, paper beats rock; same move = draw.
- TicTacToe: two players, X starts then O. Take turns marking a 3x3 grid; first to align 3 in a row/col/diag wins; board full with no line = draw.
- Guess Number (multi): 2–3 players take turns guessing a hidden number in a given range. Server replies `higher`/`lower`/`correct`; limited attempts, first correct wins; attempts exhausted with no correct guess = draw.
