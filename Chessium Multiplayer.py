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
        self.draw_agreed = False

    def update_ratings(self, outcome):
        if self.mode != "p2p":
            return

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
pygame.display.set_caption("Chessium Professional Interface")

font = pygame.font.SysFont(["segoeuisymbol", "applesymbols", "dejavusans", "arialunicode", "microsoftyahei"], 72)
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
    pygame.draw.rect(screen, (245, 245, 245), white_rect)
    pygame.draw.rect(screen, (30, 30, 30), black_rect)
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
    colors = [(235, 236, 208), (119, 149, 86)]
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
        txt_color = (119, 149, 86) if is_light_col else (235, 236, 208)
        file_surf = coord_font.render(files[i], True, txt_color)
        screen.blit(file_surf, (col_x, col_y))
        
        row_x = BOARD_SIZE - 12
        row_y = i * SQUARE + 3
        is_light_row = i % 2 == 0
        txt_color = (119, 149, 86) if is_light_row else (235, 236, 208)
        rank_surf = coord_font.render(ranks[7 - i], True, txt_color)
        screen.blit(rank_surf, (row_x, row_y))

def draw_pieces():
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            r_idx = 7 - chess.square_rank(square) if player == chess.WHITE else chess.square_rank(square)
            c_idx = chess.square_file(square) if player == chess.WHITE else 7 - chess.square_file(square)
            symbol = pieces[piece.symbol()]
            
            p_color = (255, 255, 255) if piece.color == chess.WHITE else (15, 15, 15)
            text = font.render(symbol, True, p_color)
            
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
                pygame.draw.circle(screen, (235, 94, 85), (center_x, center_y), SQUARE // 2 - 4, 5)
            else:
                surface = pygame.Surface((SQUARE, SQUARE), pygame.SRCALPHA)
                pygame.draw.circle(surface, (0, 0, 0, 45), (SQUARE // 2, SQUARE // 2), 12)
                screen.blit(surface, (c_idx * SQUARE, r_idx * SQUARE))

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
    pygame.draw.rect(screen, (30, 30, 30), ctrl_rect)
    pygame.draw.line(screen, (50, 50, 50), (0, BOARD_SIZE), (WIDTH, BOARD_SIZE), 2)
    
    elo_val = read_elo()
    if game_instance.mode == "p2p":
        text_str = f"YOUR ELO: {elo_val}  |  OPPONENT: {game_instance.opponent_elo}"
    else:
        text_str = f"YOUR ELO: {elo_val}"
    
    elo_surf = small_menu_font.render(text_str, True, (200, 200, 200))
    screen.blit(elo_surf, (15, BOARD_SIZE + 20))
    
    return None, None

def select_game_mode():
    selecting = True
    local_rect = pygame.Rect(80, 270, 220, 110)
    p2p_rect = pygame.Rect(340, 270, 220, 110)
    while selecting:
        screen.fill((30, 31, 34))
        title_text = pygame.font.SysFont("arial", 42, bold=True).render("CHESSIUM", True, (255, 255, 255))
        subtitle_text = pygame.font.SysFont("arial", 20).render("Choose your arena setup", True, (150, 150, 150))
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, 120)))
        screen.blit(subtitle_text, subtitle_text.get_rect(center=(WIDTH // 2, 170)))
        
        pygame.draw.rect(screen, (43, 45, 49), local_rect, border_radius=12)
        pygame.draw.rect(screen, (43, 45, 49), p2p_rect, border_radius=12)
        
        local_text = pygame.font.SysFont("arial", 24, bold=True).render("Pass & Play", True, (245, 245, 245))
        p2p_text = pygame.font.SysFont("arial", 24, bold=True).render("Multiplayer", True, (245, 245, 245))
        
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
    host_rect = pygame.Rect(80, 270, 220, 110)
    join_rect = pygame.Rect(340, 270, 220, 110)
    back_rect = pygame.Rect((WIDTH - 160) // 2, 430, 160, 45)
    selecting = True
    role = None
    while selecting:
        screen.fill((30, 31, 34))
        title_text = pygame.font.SysFont("arial", 42, bold=True).render("CHESSIUM ONLINE", True, (255, 255, 255))
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, 150)))
        
        pygame.draw.rect(screen, (43, 45, 49), host_rect, border_radius=12)
        pygame.draw.rect(screen, (43, 45, 49), join_rect, border_radius=12)
        pygame.draw.rect(screen, (80, 80, 80), back_rect, border_radius=8)
        
        h_text = pygame.font.SysFont("arial", 24, bold=True).render("Create Room", True, (245, 245, 245))
        j_text = pygame.font.SysFont("arial", 24, bold=True).render("Join Room", True, (245, 245, 245))
        b_text = pygame.font.SysFont("arial", 18, bold=True).render("⬅ Back", True, (255, 255, 255))
        
        screen.blit(h_text, h_text.get_rect(center=host_rect.center))
        screen.blit(j_text, j_text.get_rect(center=join_rect.center))
        screen.blit(b_text, b_text.get_rect(center=back_rect.center))
        
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
                elif back_rect.collidepoint(pos):
                    return "BACK_TO_MENU"
    
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
    input_back_rect = pygame.Rect((WIDTH - 160) // 2, 450, 160, 45)
    entering_room = True
    error_msg = ""
    
    while entering_room:
        screen.fill((30, 31, 34))
        lbl_text = "Enter Room Name to Create:" if role == "host" else "Enter Room Name to Join:"
        lbl = pygame.font.SysFont("arial", 24).render(lbl_text, True, (200, 200, 200))
        screen.blit(lbl, lbl.get_rect(center=(WIDTH // 2, 230)))
        
        pygame.draw.rect(screen, (43, 45, 49), input_box, border_radius=12)
        pygame.draw.rect(screen, (100, 100, 100), input_box, 2, border_radius=12)
        pygame.draw.rect(screen, (80, 80, 80), input_back_rect, border_radius=8)
        
        typed_surf = input_font.render(input_text, True, (255, 255, 255))
        screen.blit(typed_surf, typed_surf.get_rect(center=input_box.center))
        
        b_text = pygame.font.SysFont("arial", 18, bold=True).render("⬅ Back", True, (255, 255, 255))
        screen.blit(b_text, b_text.get_rect(center=input_back_rect.center))
        
        if error_msg:
            err_surf = pygame.font.SysFont("arial", 18, bold=True).render(error_msg, True, (240, 100, 100))
            screen.blit(err_surf, err_surf.get_rect(center=(WIDTH // 2, 400)))
            
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if input_back_rect.collidepoint(pos):
                    try:
                        sock.close()
                    except:
                        pass
                    return "BACK_TO_MENU"
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
        cancel_rect = pygame.Rect((WIDTH - 160) // 2, 400, 160, 45)
        while waiting:
            screen.fill((30, 31, 34))
            info = pygame.font.SysFont("arial", 24).render("Waiting for opponent to join...", True, (180, 180, 180))
            room_info = pygame.font.SysFont("arial", 28, bold=True).render(f"Room: {input_text}", True, (119, 149, 86))
            screen.blit(info, info.get_rect(center=(WIDTH // 2, 230)))
            screen.blit(room_info, room_info.get_rect(center=(WIDTH // 2, 290)))
            
            pygame.draw.rect(screen, (80, 80, 80), cancel_rect, border_radius=8)
            c_text = pygame.font.SysFont("arial", 18, bold=True).render("⬅ Back", True, (255, 255, 255))
            screen.blit(c_text, c_text.get_rect(center=cancel_rect.center))
            
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
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        pos = pygame.mouse.get_pos()
                        if cancel_rect.collidepoint(pos):
                            try:
                                sock.close()
                            except:
                                pass
                            return "BACK_TO_MENU"
            finally:
                sock.settimeout(None)
    else:
        waiting = True
        cancel_rect = pygame.Rect((WIDTH - 160) // 2, 400, 160, 45)
        while waiting:
            screen.fill((30, 31, 34))
            info = pygame.font.SysFont("arial", 24).render(f"Joining Room: {input_text}...", True, (180, 180, 180))
            screen.blit(info, info.get_rect(center=(WIDTH // 2, 250)))
            
            pygame.draw.rect(screen, (80, 80, 80), cancel_rect, border_radius=8)
            c_text = pygame.font.SysFont("arial", 18, bold=True).render("⬅ Back", True, (255, 255, 255))
            screen.blit(c_text, c_text.get_rect(center=cancel_rect.center))
            
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
                        try:
                            sock.close()
                        except:
                            pass
                        return "BACK_TO_MENU"
            except socket.timeout:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        pos = pygame.mouse.get_pos()
                        if cancel_rect.collidepoint(pos):
                            try:
                                sock.close()
                            except:
                                pass
                            return "BACK_TO_MENU"
            finally:
                sock.settimeout(None)

    my_elo = read_elo()
    try:
        sock.sendall(json.dumps({"type": "SHARE_ELO", "elo": my_elo}).encode('utf-8'))
    except Exception:
        pass

    return game


def show_promotion_dialog(color):
    dialog_width = 320
    dialog_height = 110
    dialog_x = (WIDTH - dialog_width) // 2
    dialog_y = (HEIGHT - dialog_height) // 2
    
    dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
    
    pieces_symbols = ["♛", "♜", "♝", "♞"] if color == chess.WHITE else ["♛", "♜", "♝", "♞"]
    piece_types = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    
    option_rects = []
    for i in range(4):
        rect = pygame.Rect(dialog_x + 15 + i * 72, dialog_y + 15, 64, 80)
        option_rects.append(rect)
        
    p_color = (255, 255, 255) if color == chess.WHITE else (30, 30, 30)

    while True:
        surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 120))
        screen.blit(surface, (0, 0))
        
        pygame.draw.rect(screen, (43, 45, 49), dialog_rect, border_radius=12)
        pygame.draw.rect(screen, (80, 80, 80), dialog_rect, 2, border_radius=12)
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, rect in enumerate(option_rects):
            if rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (60, 63, 69), rect, border_radius=8)
            else:
                pygame.draw.rect(screen, (49, 51, 56), rect, border_radius=8)
                
            symbol_surf = font.render(pieces_symbols[i], True, p_color)
            symbol_rect = symbol_surf.get_rect(center=rect.center)
            screen.blit(symbol_surf, symbol_rect)
            
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(option_rects):
                    if rect.collidepoint(event.pos):
                        return piece_types[i]


def main():
    global player, last_move_feedback, board
    
    read_elo()

    while True:
        board = chess.Board()
        last_move_feedback = None

        mode = select_game_mode()

        if mode == "p2p":
            game = connect_multiplayer()
            if game == "BACK_TO_MENU":
                continue
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
        session_active = True

        while session_active:
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
            draw_controls(game)

            game_is_over = not game.game_active or board.is_game_over()

            if game_is_over:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                
                res_str = "Match Concluded"
                if board.is_checkmate():
                    res_str = "Checkmate! Game Over"
                elif board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw() or game.draw_agreed:
                    res_str = "Match ended in a Draw"
                    
                txt_surf = game_over_font.render(res_str, True, (255, 255, 255))
                screen.blit(txt_surf, txt_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
                
                sub_surf = small_menu_font.render("Click anywhere to return to Main Menu", True, (200, 200, 200))
                screen.blit(sub_surf, sub_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

            pygame.display.flip()
            clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = pygame.mouse.get_pos()
                    
                    if game_is_over:
                        session_active = False
                        break

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
                            piece = board.piece_at(square_idx)
                            if piece and piece.color == board.turn:
                                selected_sq = square_idx
                            else:
                                moving_piece = board.piece_at(selected_sq)
                                is_promotion = False
                                
                                if moving_piece and moving_piece.piece_type == chess.PAWN:
                                    from_rank = chess.square_rank(selected_sq)
                                    to_rank = chess.square_rank(square_idx)
                                    if (moving_piece.color == chess.WHITE and from_rank == 6 and to_rank == 7) or \
                                       (moving_piece.color == chess.BLACK and from_rank == 1 and to_rank == 0):
                                        is_promotion = True

                                if is_promotion:
                                    temp_move = chess.Move(selected_sq, square_idx, promotion=chess.QUEEN)
                                    if temp_move in board.legal_moves:
                                        chosen_piece = show_promotion_dialog(moving_piece.color)
                                        move = chess.Move(selected_sq, square_idx, promotion=chosen_piece)
                                    else:
                                        move = chess.Move(selected_sq, square_idx)
                                else:
                                    move = chess.Move(selected_sq, square_idx)

                                if move in board.legal_moves:
                                    quality_tag, symbol, color = get_move_quality(board, move, 2)
                                    last_move_feedback = (move.uci(), symbol, color, pygame.time.get_ticks())
                                    
                                    play_move_sound(board, move)
                                    board.push(move)
                                    
                                    if mode == "local":
                                        player = board.turn
                                    
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
