import argparse, socket, time
from .protocol import send_json, recv_json

MOVE_MAP = {
    "1": "rock",
    "2": "paper",
    "3": "scissors",
    "rock": "rock",
    "paper": "paper",
    "scissors": "scissors",
}


def pick_move(round_num: int) -> str:
    raw = input(f"[Round {round_num}] Your move (1=rock, 2=paper, 3=scissors): ").strip()
    mv = MOVE_MAP.get(raw.lower()) if raw else None
    return mv or "rock"


def main(host, port, username, room_id, token):
    with socket.create_connection((host, port)) as sock:
        send_json(sock, {
            "cmd": "join",
            "username": username,
            "room_id": room_id,
            "token": token
        })
        while True:
            try:
                msg = recv_json(sock)
            except:
                print("One of the oppoents disconnected.")
                time.sleep(1)
                print("You will go back to the lobby...")
                time.sleep(1)
                print(".")
                time.sleep(1)
                print(".")
                time.sleep(1)
                print(".")
                break
            if msg is None:
                print("One of the oppoents disconnected.")
                time.sleep(1)
                print("You will go back to the lobby...")
                time.sleep(1)
                print(".")
                time.sleep(1)
                print(".")
                time.sleep(1)
                print(".")
                break

            cmd = msg.get("cmd")
            if cmd == "ask_move":
                round_num = msg.get("round", 0)
                mv = pick_move(round_num)
                send_json(sock, {"cmd": "move", "move": mv})
                print("Wait for the oppoent select the option")
            elif cmd == "round_start":
                scores = msg.get("scores") or {}
                print(f"\n=== Round {msg.get('round')} ===")
                print(f"Scores: P1={scores.get('p1',0)}  P2={scores.get('p2',0)}")
            elif cmd == "round_result":
                p1, p2 = msg.get("p1", {}), msg.get("p2", {})
                print(f"Round {msg.get('round')} result: {p1.get('user')}[{p1.get('move')}] vs {p2.get('user')}[{p2.get('move')}] -> {msg.get('winner')}")
                scores = msg.get("scores") or {}
                print(f"Updated scores: P1={scores.get('p1',0)}  P2={scores.get('p2',0)}")
            elif cmd == "game_over":
                print("\n=== Game Over ===")
                print(f"Rounds played: {msg.get('rounds')}")
                print(f"Final scores: {msg.get('scores')}")
                print(f"Result: {msg.get('result')}")
                time.sleep(1)
                print("You will go back to the lobby...")
                time.sleep(1)
                print(".")
                time.sleep(1)
                print(".")
                time.sleep(1)
                print(".")
            elif cmd == "error":
                print(f"Error from server: {msg.get('message')}")
            else:
                print(f"Unknown message: {msg}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=23456)
    ap.add_argument("--user", default="player")
    ap.add_argument("--room-id", type=int, default=None)
    ap.add_argument("--token", default=None)
    args = ap.parse_args()
    main(args.host, args.port, args.user, args.room_id, args.token)
