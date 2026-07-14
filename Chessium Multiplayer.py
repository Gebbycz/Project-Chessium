import os
import pygame
import chess
import sys
import math
import array
import json
import socket
import threading
import stat

SERVER_IP = "bore.pub"
SERVER_PORT = 45617

player = chess.WHITE  

ELO_FILE = "elo.txt"
DEFAULT_ELO = 1000

def read_elo():
    if not os.path.exists(ELO_FILE):
        write_elo(DEFAULT_ELO)
        return DEFAULT_ELO
    try:
        with open(ELO_FILE, "r") as f:
            return int(f.read().strip())
    except Exception:
        return DEFAULT_ELO

def write_elo(val):
    if os.path.exists(ELO_FILE):
        try:
            os.chmod(ELO_FILE, stat.S_IWRITE)
        except Exception:
            pass
            
    try:
        with open(ELO_FILE, "w") as f:
            f.write(str(val))
    except Exception as e:
        print(f"Error writing ELO: {e}")
        
    try:
        os.chmod(ELO_FILE, stat.S_IREAD)
    except Exception:
        pass


class ChessGame:
    def __init__(self, mode="local"):
        self.mode = mode
        self.is_host = False
        self.conn = None
        self.game_active = True
        self.my_turn = True
        self.opponent_elo = 1000
        self.draw_requested_by_opponent = False

    def resign(self):
        if not self.game_active:
            return

        self.game_active = False

        if self.mode == "p2p" and self.conn:
            packet = {"type": "RESIGN"}
            try:
                self.conn.sendall(json.dumps(packet).encode('utf-8'))
            except Exception:
                pass
            self.update_ratings(outcome="loss")
        else:
            self.update_ratings(outcome="loss")

    def offer_draw(self):
        if not self.game_active:
            return

        if self.mode == "p2p" and self.conn:
            if self.draw_requested_by_opponent:
                self.game_active = False
                packet = {"type": "DRAW_RESPONSE", "accepted": True}
                try:
                    self.conn.sendall(json.dumps(packet).encode('utf-8'))
                except Exception:
                    pass
                self.update_ratings(outcome="draw")
            else:
                packet = {"type": "DRAW_OFFER"}
                try:
                    self.conn.sendall(json.dumps(packet).encode('utf-8'))
                except Exception:
                    pass
        elif self.mode == "local":
            self.game_active = False
            self.update_ratings(outcome="draw")

    def update_ratings(self, outcome):
        current_elo = read_elo()
        
        if outcome == "win":
            S_A = 1.0
        elif outcome == "loss":
            S_A = 0.0
        else:
            S_A = 0.5
            
        E_A = 1 / (1 + 10 ** ((self.opponent_elo - current_elo) / 400.0))
        
        new_elo = round(current_elo + 32 * (S_A - E_A))
        new_elo = max(100, new_elo)
        
        write_elo(new_elo)

    def start_p2p_listener(self, on_move_callback):
        def listen():
            while self.game_active:
                try:
                    data = self.conn.recv(2048)
                    if not data:
                        break
                    packet = json.loads(data.decode('utf-8'))
                    if packet["type"] == "MOVE":
                        on_move_callback(packet["move"])
                    elif packet["type"] == "RESIGN":
                        self.game_active = False
                        self.update_ratings(outcome="win")
                        break
                    elif packet["type"] == "DRAW_OFFER":
                        self.draw_requested_by_opponent = True
                    elif packet["type"] == "DRAW_RESPONSE":
                        if packet.get("accepted"):
                            self.game_active = False
                            self.update_ratings(outcome="draw")
                    elif packet["type"] == "SHARE_ELO":
                        self.opponent_elo = packet["elo"]
                except Exception:
                    break
        threading.Thread(target=listen, daemon=True).start()


def check_if_draw(board):
    return (
        board.is_stalemate() 
        or board.is_insufficient_material() 
        or board.can_claim_draw()
    )

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1)

BOARD_SIZE = 640
BAR_WIDTH = 40
CONTROL_HEIGHT = 60
WIDTH = BOARD_SIZE + BAR_WIDTH
HEIGHT = BOARD_SIZE + CONTROL_HEIGHT
SQUARE = BOARD_SIZE // 8

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chessium Multiplayer Lobby")

font = pygame.font.SysFont(["segoeuisymbol", "applesymbols", "dejavusans", "arialunicode", "microsoftyahei"], 70)
menu_font = pygame.font.SysFont("arial", 30, bold=True)
small_menu_font = pygame.font.SysFont("arial", 18, bold=True)
input_font = pygame.font.SysFont("arial", 40, bold=True)
game_over_font = pygame.font.SysFont("arial", 45, bold=True)
eval_font = pygame.font.SysFont("arial", 14, bold=True)
feedback_font = pygame.font.SysFont(["segoeuisymbol", "applesymbols", "dejavusans", "arialunicode", "microsoftyahei"], 55)
coord_font = pygame.font.SysFont("arial", 14, bold=True)
button_font = pygame.font.SysFont("arial", 12, bold=True)

board = chess.Board()

pieces = {
    "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
    "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"
}

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0
}

PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_TABLE = [
      0,  0,  0,  0,  0,  0,  0,  0,
      5, 10, 10, 10, 10, 10, 10,  5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
     -5,  0,  0,  0,  0,  0,  0, -5,
      0,  0,  0,  5,  5,  5,  0,  0
]

QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0,  0,
    -10,  5,  5,  5,  5,  5,  5,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

BOOK_OPENINGS = {
    "e2e4": ("Book", "📖", (50, 150, 250)),
    "d2d4": ("Book", "📖", (50, 150, 250)),
    "g1f3": ("Book", "📖", (50, 150, 250)),
    "c2c4": ("Book", "📖", (50, 150, 250)),
    "e7e5": ("Book", "📖", (50, 150, 250)),
    "c7c5": ("Book", "📖", (50, 150, 250)),
    "e7e6": ("Book", "📖", (50, 150, 250)),
    "d7d5": ("Book", "📖", (50, 150, 250)),
    "g8f6": ("Book", "📖", (50, 150, 250)),
    "b8c6": ("Book", "📖", (50, 150, 250)),
}

last_move_feedback = None

def generate_sound(freq1, freq2, duration, volume=0.3):
    sample_rate = 22050
    num_samples = int(duration * sample_rate)
    buffer = array.array('h')
    for i in range(num_samples):
        t = i / sample_rate
        freq = freq1 + (freq2 - freq1) * (i / num_samples)
        val = math.sin(2 * math.pi * freq * t)
        envelope = 1.0 - (i / num_samples)
        sample = int(val * 32767 * volume * envelope)
        buffer.append(sample)
    return pygame.mixer.Sound(buffer)

sound_move = generate_sound(450, 450, 0.08, 0.25)
sound_capture = generate_sound(300, 200, 0.12, 0.3)
sound_check = generate_sound(550, 680, 0.18, 0.35)

def evaluate_board(b):
    if b.is_checkmate():
        if b.turn == chess.WHITE:
            return -99999
        else:
            return 99999
    if b.is_stalemate() or b.is_insufficient_material():
        return 0

    score = 0
    for square in chess.SQUARES:
        piece = b.piece_at(square)
        if piece:
            val = PIECE_VALUES[piece.piece_type]            
            idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
            if piece.piece_type == chess.PAWN:
                val += PAWN_TABLE[idx]
            elif piece.piece_type == chess.KNIGHT:
                val += KNIGHT_TABLE[idx]
            elif piece.piece_type == chess.BISHOP:
                val += BISHOP_TABLE[idx]
            elif piece.piece_type == chess.ROOK:
                val += ROOK_TABLE[idx]
            elif piece.piece_type == chess.QUEEN:
                val += QUEEN_TABLE[idx]

            if piece.color == chess.WHITE:
                score += val
            else:
                score -= val
    return score

def score_move(b, move):
    score = 0
    if b.gives_check(move):
        score += 50
    if move.promotion:
        score += 40
    if b.is_capture(move):
        attacker = b.piece_at(move.from_square)
        target = b.piece_at(move.to_square)
        if attacker and target:
            score += (PIECE_VALUES[target.piece_type] * 10) - PIECE_VALUES[attacker.piece_type]
        else:
            score += 10
    return score

def quiescence_search(b, alpha, beta, maximizing_player):
    stand_pat = evaluate_board(b)
    if maximizing_player:
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat
        for move in b.legal_moves:
            if b.is_capture(move):
                b.push(move)
                score = quiescence_search(b, alpha, beta, False)
                b.pop()
                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score
        return alpha
    else:
        if stand_pat <= alpha:
            return alpha
        if stand_pat < beta:
            beta = stand_pat
        for move in b.legal_moves:
            if b.is_capture(move):
                b.push(move)
                score = quiescence_search(b, alpha, beta, True)
                b.pop()
                if score <= alpha:
                    return alpha
                if score < beta:
                    beta = score
        return beta

def alpha_beta(b, depth, alpha, beta, maximizing_player):
    if b.is_game_over():
        return evaluate_board(b), None
    if depth == 0:
        return quiescence_search(b, alpha, beta, maximizing_player), None

    moves = list(b.legal_moves)
    moves.sort(key=lambda m: score_move(b, m), reverse=True)
    best_move = None

    if maximizing_player:
        max_eval = -float('inf')
        for move in moves:
            b.push(move)
            evaluation, _ = alpha_beta(b, depth - 1, alpha, beta, False)
            b.pop()
            if evaluation > max_eval:
                max_eval = evaluation
                best_move = move
            alpha = max(alpha, evaluation)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = float('inf')
        for move in moves:
            b.push(move)
            evaluation, _ = alpha_beta(b, depth - 1, alpha, beta, True)
            b.pop()
            if evaluation < min_eval:
                min_eval = evaluation
                best_move = move
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval, best_move

def play_move_sound(b, move):
    if b.gives_check(move):
        sound_check.play()
    elif b.is_capture(move):
        sound_capture.play()
    else:
        sound_move.play()

def get_move_quality(b, move, max_depth):
    move_str = move.uci()
    if move_str in BOOK_OPENINGS and b.fullmove_number <= 8:
        return BOOK_OPENINGS[move_str]

    is_white = b.turn == chess.WHITE
    analysis_depth = min(3, max_depth)
    
    b.push(move)
    after_eval, _ = alpha_beta(b, max(1, analysis_depth - 1), -float('inf'), float('inf'), not is_white)
    b.pop()
    
    eval_sign = 1 if is_white else -1
    relative_after = after_eval * eval_sign
    
    best_val = -float('inf') if is_white else float('inf')
    best_move = None
    for legal in b.legal_moves:
        b.push(legal)
        val, _ = alpha_beta(b, max(1, analysis_depth - 1), -float('inf'), float('inf'), not is_white)
        b.pop()
        if is_white:
            if val > best_val:
                best_val = val
                best_move = legal
        else:
            if val < best_val:
                best_val = val
                best_move = legal
                
    relative_best = best_val * eval_sign
    diff = relative_best - relative_after
    
    if move == best_move or diff <= 5:
        return ("Best Move", "⭐", (255, 215, 0))
    elif diff <= 40:
        return ("Excellent", "✨", (30, 200, 80))
    elif diff <= 120:
        return ("Good", "👍", (150, 220, 50))
    elif diff <= 300:
        return ("Inaccuracy", "?!", (240, 180, 20))
    elif diff <= 600:
        return ("Mistake", "?", (230, 110, 30))
    else:
        return ("Blunder", "??", (220, 40, 40))

def draw_evaluation_bar(curr_eval):
    bar_rect = pygame.Rect(BOARD_SIZE, 0, BAR_WIDTH, BOARD_SIZE)
    pygame.draw.rect(screen, (30, 30, 30), bar_rect)
    clamped_eval = max(-1000, min(1000, curr_eval))
    normalized = (clamped_eval + 1000) / 2000.0
    if player == chess.BLACK:
        normalized = 1.0 - normalized
    white_height = int(BOARD_SIZE * normalized)
    white_rect = pygame.Rect(BOARD_SIZE, BOARD_SIZE - white_height, BAR_WIDTH, white_height)
    black_rect = pygame.Rect(BOARD_SIZE, 0, BAR_WIDTH, BOARD_SIZE - white_height)
    pygame.draw.rect(screen, (240, 240, 240), white_rect)
    pygame.draw.rect(screen, (40, 40, 40), black_rect)
    eval_val = curr_eval / 100.0
    eval_text = f"+{eval_val:.1f}" if eval_val > 0 else f"{eval_val:.1f}"
    if abs(curr_eval) > 50000:
        eval_text = "M"
    text_surf = eval_font.render(eval_text, True, (120, 120, 120))
    text_rect = text_surf.get_rect()
    if white_height > BOARD_SIZE // 2:
        text_rect.center = (BOARD_SIZE + BAR_WIDTH // 2, BOARD_SIZE - 30)
    else:
        text_rect.center = (BOARD_SIZE + BAR_WIDTH // 2, 30)
    screen.blit(text_surf, text_rect)

def draw_board():
    colors = [(240, 217, 181), (181, 136, 99)]
    for row in range(8):
        for col in range(8):
            color = colors[(row + col) % 2]
            pygame.draw.rect(screen, color, (col * SQUARE, row * SQUARE, SQUARE, SQUARE))

def draw_coordinates():
    files = ["a", "b", "c", "d", "e", "f", "g", "h"]
    ranks = ["1", "2", "3", "4", "5", "6", "7", "8"]
    if player == chess.BLACK:
        files.reverse()
        ranks.reverse()
    for i in range(8):
        col_x = i * SQUARE + 5
        col_y = BOARD_SIZE - 18
        is_light_col = (7 + i) % 2 == 0
        txt_color = (181, 136, 99) if is_light_col else (240, 217, 181)
        file_surf = coord_font.render(files[i], True, txt_color)
        screen.blit(file_surf, (col_x, col_y))
        
        row_x = BOARD_SIZE - 12
        row_y = i * SQUARE + 3
        is_light_row = i % 2 == 0
        txt_color = (181, 136, 99) if is_light_row else (240, 217, 181)
        rank_surf = coord_font.render(ranks[7 - i], True, txt_color)
        screen.blit(rank_surf, (row_x, row_y))

def draw_pieces():
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            r_idx = 7 - chess.square_rank(square) if player == chess.WHITE else chess.square_rank(square)
            c_idx = chess.square_file(square) if player == chess.WHITE else 7 - chess.square_file(square)
            symbol = pieces[piece.symbol()]
            text = font.render(symbol, True, (0, 0, 0))
            rect = text.get_rect(center=(c_idx * SQUARE + SQUARE // 2, r_idx * SQUARE + SQUARE // 2))
            screen.blit(text, rect)

def draw_legal_destinations(selected_sq):
    if selected_sq is None:
        return
    for move in board.legal_moves:
        if move.from_square == selected_sq:
            to_sq = move.to_square
            r_idx = 7 - chess.square_rank(to_sq) if player == chess.WHITE else chess.square_rank(to_sq)
            c_idx = chess.square_file(to_sq) if player == chess.WHITE else 7 - chess.square_file(to_sq)
            center_x = c_idx * SQUARE + SQUARE // 2
            center_y = r_idx * SQUARE + SQUARE // 2
            if board.piece_at(to_sq):
                pygame.draw.circle(screen, (220, 60, 60), (center_x, center_y), SQUARE // 2 - 4, 5)
            else:
                pygame.draw.circle(screen, (100, 100, 100, 150), (center_x, center_y), 10)

def draw_feedback():
    if last_move_feedback:
        move_str, symbol, color, stamp = last_move_feedback
        if pygame.time.get_ticks() - stamp < 1500:
            square_str = move_str[2:4]
            to_square = chess.parse_square(square_str)
            r_idx = 7 - chess.square_rank(to_square) if player == chess.WHITE else chess.square_rank(to_square)
            c_idx = chess.square_file(to_square) if player == chess.WHITE else 7 - chess.square_file(to_square)
            
            bg_surf = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
            bg_surf.fill(list(color) + [80])
            screen.blit(bg_surf, (c_idx * SQUARE, r_idx * SQUARE))
            
            sym_surf = feedback_font.render(symbol, True, color)
            sym_rect = sym_surf.get_rect(center=(c_idx * SQUARE + SQUARE // 2, r_idx * SQUARE + SQUARE // 2 - 10))
            screen.blit(sym_surf, sym_rect)

def draw_controls(game_instance):
    ctrl_rect = pygame.Rect(0, BOARD_SIZE, WIDTH, CONTROL_HEIGHT)
    pygame.draw.rect(screen, (35, 35, 35), ctrl_rect)
    pygame.draw.line(screen, (60, 60, 60), (0, BOARD_SIZE), (WIDTH, BOARD_SIZE), 2)
    
    elo_val = read_elo()
    if game_instance.mode == "p2p":
        text_str = f"YOUR ELO: {elo_val}  |  OPPONENT: {game_instance.opponent_elo}"
    else:
        text_str = f"YOUR ELO: {elo_val}"
    
    elo_surf = small_menu_font.render(text_str, True, (255, 215, 0))
    screen.blit(elo_surf, (15, BOARD_SIZE + 20))
    
    # 2x smaller buttons centered vertically in the bottom bar
    resign_btn = pygame.Rect(420, BOARD_SIZE + 20, 80, 20)
    pygame.draw.rect(screen, (150, 50, 50), resign_btn, border_radius=3)
    pygame.draw.rect(screen, (220, 100, 100), resign_btn, 1, border_radius=3)
    resign_txt = button_font.render("🏳️ RESIGN", True, (255, 255, 255))
    screen.blit(resign_txt, resign_txt.get_rect(center=resign_btn.center))
    
    draw_btn = pygame.Rect(510, BOARD_SIZE + 20, 80, 20)
    
    draw_color = (200, 160, 40) if game_instance.draw_requested_by_opponent else (70, 100, 150)
    draw_border = (255, 215, 0) if game_instance.draw_requested_by_opponent else (120, 160, 220)
    
    pygame.draw.rect(screen, draw_color, draw_btn, border_radius=3)
    pygame.draw.rect(screen, draw_border, draw_btn, 1, border_radius=3)
    draw_txt = button_font.render("🤝 DRAW", True, (255, 255, 255))
    screen.blit(draw_txt, draw_txt.get_rect(center=draw_btn.center))
    
    return resign_btn, draw_btn

def select_game_mode():
    selecting = True
    local_rect = pygame.Rect(100, 270, 200, 100)
    p2p_rect = pygame.Rect(340, 270, 200, 100)
    while selecting:
        screen.fill((50, 50, 50))
        title_text = pygame.font.SysFont("arial", 40, bold=True).render("Select Game Mode", True, (255, 255, 255))
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, 150)))
        
        pygame.draw.rect(screen, (140, 210, 120), local_rect, border_radius=10)
        pygame.draw.rect(screen, (240, 140, 120), p2p_rect, border_radius=10)
        
        local_text = pygame.font.SysFont("arial", 22, bold=True).render("Pass & Play", True, (20, 20, 20))
        p2p_text = pygame.font.SysFont("arial", 22, bold=True).render("Multiplayer", True, (20, 20, 20))
        
        screen.blit(local_text, local_text.get_rect(center=local_rect.center))
        screen.blit(p2p_text, p2p_text.get_rect(center=p2p_rect.center))
        
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if local_rect.collidepoint(pos):
                    return "local"
                if p2p_rect.collidepoint(pos):
                    return "p2p"

def connect_multiplayer():
    host_rect = pygame.Rect(80, 270, 200, 100)
    join_rect = pygame.Rect(360, 270, 200, 100)
    selecting = True
    role = None
    while selecting:
        screen.fill((50, 50, 50))
        title_text = pygame.font.SysFont("arial", 40, bold=True).render("Connection Setup", True, (255, 255, 255))
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, 150)))
        pygame.draw.rect(screen, (100, 200, 120), host_rect, border_radius=10)
        pygame.draw.rect(screen, (240, 180, 80), join_rect, border_radius=10)
        h_text = pygame.font.SysFont("arial", 30, bold=True).render("Create Room", True, (20, 20, 20))
        j_text = pygame.font.SysFont("arial", 30, bold=True).render("Join Room", True, (20, 20, 20))
        screen.blit(h_text, h_text.get_rect(center=host_rect.center))
        screen.blit(j_text, j_text.get_rect(center=join_rect.center))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if host_rect.collidepoint(pos):
                    role = "host"
                    selecting = False
                elif join_rect.collidepoint(pos):
                    role = "join"
                    selecting = False
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_IP, SERVER_PORT))
    except Exception:
        print("Could not connect to central server.")
        pygame.quit()
        sys.exit()

    game = ChessGame(mode="p2p")
    game.conn = sock
    
    input_text = ""
    input_box = pygame.Rect((WIDTH - 300) // 2, 300, 300, 60)
    entering_room = True
    error_msg = ""
    
    while entering_room:
        screen.fill((50, 50, 50))
        lbl_text = "Enter Room Name to Create:" if role == "host" else "Enter Room Name to Join:"
        lbl = pygame.font.SysFont("arial", 24).render(lbl_text, True, (255, 255, 255))
        screen.blit(lbl, lbl.get_rect(center=(WIDTH // 2, 230)))
        
        pygame.draw.rect(screen, (30, 30, 30), input_box, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), input_box, 3, border_radius=10)
        
        typed_surf = input_font.render(input_text, True, (255, 255, 255))
        screen.blit(typed_surf, typed_surf.get_rect(center=input_box.center))
        
        if error_msg:
            err_surf = pygame.font.SysFont("arial", 18, bold=True).render(error_msg, True, (255, 100, 100))
            screen.blit(err_surf, err_surf.get_rect(center=(WIDTH // 2, 400)))
            
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_RETURN:
                    if len(input_text) > 0:
                        if role == "host":
                            sock.sendall(json.dumps({"type": "CREATE", "room_id": input_text}).encode('utf-8'))
                            resp = json.loads(sock.recv(1024).decode('utf-8'))
                            if resp.get("status") == "ok":
                                game.is_host = True
                                entering_room = False
                            else:
                                error_msg = "Room already exists!"
                        else:
                            sock.sendall(json.dumps({"type": "JOIN", "room_id": input_text}).encode('utf-8'))
                            entering_room = False
                else:
                    if len(input_text) < 12 and event.unicode.isalnum():
                        input_text += event.unicode

    if role == "host":
        waiting = True
        while waiting:
            screen.fill((50, 50, 50))
            info = pygame.font.SysFont("arial", 24).render(f"Waiting for opponent to join...", True, (255, 255, 255))
            room_info = pygame.font.SysFont("arial", 28, bold=True).render(f"Room: {input_text}", True, (100, 240, 120))
            screen.blit(info, info.get_rect(center=(WIDTH // 2, 250)))
            screen.blit(room_info, room_info.get_rect(center=(WIDTH // 2, 320)))
            pygame.display.flip()
            
            sock.settimeout(0.1)
            try:
                data = sock.recv(1024)
                if data:
                    packet = json.loads(data.decode('utf-8'))
                    if packet.get("type") == "START":
                        global player
                        player = chess.WHITE
                        game.my_turn = True
                        waiting = False
            except socket.timeout:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
            finally:
                sock.settimeout(None)
    else:
        waiting = True
        while waiting:
            screen.fill((50, 50, 50))
            info = pygame.font.SysFont("arial", 24).render(f"Joining Room: {input_text}...", True, (255, 255, 255))
            screen.blit(info, info.get_rect(center=(WIDTH // 2, 250)))
            pygame.display.flip()
            
            sock.settimeout(0.1)
            try:
                data = sock.recv(1024)
                if data:
                    packet = json.loads(data.decode('utf-8'))
                    if packet.get("type") == "START":
                        player = chess.BLACK
                        game.my_turn = False
                        waiting = False
                    elif packet.get("type") == "JOIN_RESPONSE" and packet.get("status") == "fail":
                        print("Failed to join room.")
                        pygame.quit()
                        sys.exit()
            except socket.timeout:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
            finally:
                sock.settimeout(None)

    my_elo = read_elo()
    try:
        sock.sendall(json.dumps({"type": "SHARE_ELO", "elo": my_elo}).encode('utf-8'))
    except Exception:
        pass

    return game


def main():
    global player, last_move_feedback
    
    read_elo()

    mode = select_game_mode()

    if mode == "p2p":
        game = connect_multiplayer()
    else:
        game = ChessGame(mode="local")
        player = chess.WHITE
        game.my_turn = True

    if mode == "p2p":
        def on_remote_move(move_uci):
            move = chess.Move.from_uci(move_uci)
            if move in board.legal_moves:
                play_move_sound(board, move)
                board.push(move)
                game.my_turn = True

        game.start_p2p_listener(on_remote_move)

    selected_sq = None
    clock = pygame.time.Clock()

    while True:
        curr_eval = evaluate_board(board)

        if game.game_active and board.is_game_over():
            game.game_active = False
            result = board.result()
            if result == "1-0":
                outcome = "win" if player == chess.WHITE else "loss"
            elif result == "0-1":
                outcome = "win" if player == chess.BLACK else "loss"
            else:
                outcome = "draw"
            game.update_ratings(outcome)

        draw_board()
        draw_coordinates()
        draw_pieces()
        draw_legal_destinations(selected_sq)
        draw_evaluation_bar(curr_eval)
        draw_feedback()
        resign_btn, draw_btn = draw_controls(game)

        if game.game_active and game.draw_requested_by_opponent:
            overlay_height = 40
            alert_bar = pygame.Rect(0, 0, WIDTH, overlay_height)
            pygame.draw.rect(screen, (220, 160, 40), alert_bar)
            alert_font = pygame.font.SysFont("arial", 18, bold=True)
            alert_text = alert_font.render("Draw requested! Click on DRAW to end.", True, (255, 255, 255))
            screen.blit(alert_text, alert_text.get_rect(center=alert_bar.center))

        if not game.game_active or board.is_game_over():
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            
            res_str = "Match Concluded"
            if board.is_checkmate():
                res_str = "Checkmate! Game Over"
            elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw() or (not game.game_active and not board.is_game_over()):
                res_str = "Match ended in a Draw"
                
            txt_surf = game_over_font.render(res_str, True, (255, 255, 255))
            screen.blit(txt_surf, txt_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                
                if resign_btn.collidepoint(pos):
                    game.resign()
                    continue
                if draw_btn.collidepoint(pos):
                    game.offer_draw()
                    continue

                if not game.game_active or (mode == "p2p" and not game.my_turn):
                    continue

                col = pos[0] // SQUARE
                row = pos[1] // SQUARE

                if col < 8 and row < 8:
                    square_idx = (7 - row) * 8 + col if player == chess.WHITE else row * 8 + (7 - col)
                    
                    if selected_sq is None:
                        piece = board.piece_at(square_idx)
                        if piece and piece.color == board.turn:
                            selected_sq = square_idx
                    else:
                        move = chess.Move(selected_sq, square_idx)
                        
                        if board.piece_at(selected_sq) and board.piece_at(selected_sq).piece_type == chess.PAWN:
                            if chess.square_rank(square_idx) in [0, 7]:
                                move = chess.Move(selected_sq, square_idx, promotion=chess.QUEEN)

                        if move in board.legal_moves:
                            quality_tag, symbol, color = get_move_quality(board, move, 2)
                            last_move_feedback = (move.uci(), symbol, color, pygame.time.get_ticks())
                            
                            play_move_sound(board, move)
                            board.push(move)
                            
                            if mode == "p2p" and game.conn:
                                packet = {"type": "MOVE", "move": move.uci()}
                                try:
                                    game.conn.sendall(json.dumps(packet).encode('utf-8'))
                                except Exception:
                                    pass
                                game.my_turn = False
                            selected_sq = None


if __name__ == "__main__":
    main()
