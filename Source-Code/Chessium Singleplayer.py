import os
import random
import pygame
import chess
import sys
import math
import array
import json

player = chess.WHITE  

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
pygame.display.set_caption("Chessium 1.1")

font = pygame.font.SysFont(["segoeuisymbol", "applesymbols", "dejavusans", "arialunicode", "microsoftyahei"], 70)
menu_font = pygame.font.SysFont("arial", 30, bold=True)
small_menu_font = pygame.font.SysFont("arial", 18, bold=True)
input_font = pygame.font.SysFont("arial", 40, bold=True)
game_over_font = pygame.font.SysFont("arial", 60, bold=True)
eval_font = pygame.font.SysFont("arial", 14, bold=True)
feedback_font = pygame.font.SysFont(["segoeuisymbol", "applesymbols", "dejavusans", "arialunicode", "microsoftyahei"], 55)
coord_font = pygame.font.SysFont("arial", 14, bold=True)
button_font = pygame.font.SysFont("arial", 20, bold=True)

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

def smart_move(b, elo, max_depth):
    moves = list(b.legal_moves)
    if not moves:
        return None

    if elo <= 300:
        blunder_chance = 0.50
    elif elo <= 600:
        blunder_chance = 0.30
    elif elo <= 1100:
        blunder_chance = 0.15
    elif elo <= 1600:
        blunder_chance = 0.05
    elif elo <= 2100:
        blunder_chance = 0.02
    else:
        blunder_chance = 0.0

    if random.random() < blunder_chance:
        playable_moves = []
        for m in moves:
            b.push(m)
            gives_checkmate = b.is_checkmate()
            b.pop()
            if not gives_checkmate:
                playable_moves.append(m)
        if playable_moves:
            return random.choice(playable_moves)

    is_maximizing = b.turn == chess.WHITE
    _, move = alpha_beta(b, max_depth, -float('inf'), float('inf'), is_maximizing)
    if move is None:
        move = random.choice(moves)
    return move

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

def draw_controls():
    ctrl_rect = pygame.Rect(0, BOARD_SIZE, WIDTH, CONTROL_HEIGHT)
    pygame.draw.rect(screen, (35, 35, 35), ctrl_rect)
    pygame.draw.line(screen, (60, 60, 60), (0, BOARD_SIZE), (WIDTH, BOARD_SIZE), 2)
    
    undo_btn = pygame.Rect(20, BOARD_SIZE + 10, 140, 40)
    pygame.draw.rect(screen, (70, 70, 70), undo_btn, border_radius=5)
    pygame.draw.rect(screen, (120, 120, 120), undo_btn, 2, border_radius=5)
    
    txt = button_font.render("↩ UNDO", True, (240, 240, 240))
    screen.blit(txt, txt.get_rect(center=undo_btn.center))
    
    return undo_btn


def draw_back_button():
    back_btn = pygame.Rect(20, 20, 100, 40)
    pygame.draw.rect(screen, (180, 80, 80), back_btn, border_radius=6)
    pygame.draw.rect(screen, (255, 255, 255), back_btn, 2, border_radius=6)
    txt = button_font.render("← BACK", True, (255, 255, 255))
    screen.blit(txt, txt.get_rect(center=back_btn.center))
    return back_btn

def select_game_mode():
    selecting = True
    bot_rect = pygame.Rect(100, 270, 200, 100)
    local_rect = pygame.Rect(380, 270, 200, 100)
    
    while selecting:
        screen.fill((40, 40, 45)) 
        
        title_font = pygame.font.SysFont("arial", 50, bold=True)
        title_text = title_font.render("CHESSIUM", True, (255, 255, 255))
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, 120)))
        
        sub_font = pygame.font.SysFont("arial", 22)
        sub_text = sub_font.render("Choose your arena setup", True, (180, 180, 180))
        screen.blit(sub_text, sub_text.get_rect(center=(WIDTH // 2, 170)))
        
        pygame.draw.rect(screen, (50, 50, 55), bot_rect, border_radius=10)
        pygame.draw.rect(screen, (50, 50, 55), local_rect, border_radius=10)
        
        btn_font = pygame.font.SysFont("arial", 24, bold=True)
        bot_text = btn_font.render("Play Bot", True, (255, 255, 255))
        local_text = btn_font.render("Pass & Play", True, (255, 255, 255))
        
        screen.blit(bot_text, bot_text.get_rect(center=bot_rect.center))
        screen.blit(local_text, local_text.get_rect(center=local_rect.center))
        
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if bot_rect.collidepoint(pos):
                    return "bot"
                if local_rect.collidepoint(pos):
                    return "local"

def select_color():
    selecting = True
    white_rect = pygame.Rect(80, 270, 200, 100)
    black_rect = pygame.Rect(360, 270, 200, 100)
    while selecting:
        screen.fill((50, 50, 50))
        title_text = pygame.font.SysFont("arial", 40, bold=True).render("Choose Your Side", True, (255, 255, 255))
        back_btn = draw_back_button()
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, 150)))
        pygame.draw.rect(screen, (240, 240, 240), white_rect, border_radius=10)
        pygame.draw.rect(screen, (20, 20, 20), black_rect, border_radius=10)
        w_text = pygame.font.SysFont("arial", 35, bold=True).render("White", True, (0, 0, 0))
        b_text = pygame.font.SysFont("arial", 35, bold=True).render("Black", True, (255, 255, 255))
        screen.blit(w_text, w_text.get_rect(center=white_rect.center))
        screen.blit(b_text, b_text.get_rect(center=black_rect.center))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if back_btn.collidepoint(pos):
                    return "BACK"
                if white_rect.collidepoint(pos):
                    return chess.WHITE
                if black_rect.collidepoint(pos):
                    return chess.BLACK

def select_difficulty():
    levels = [
        ("Starter", 200, (80, 200, 120)),
        ("Beginner", 500, (100, 180, 240)),
        ("Amateur", 1000, (240, 210, 80)),
        ("Intermediate", 1500, (240, 150, 80)),
        ("Pro", 2000, (230, 90, 90)),
        ("Max", 2550, (180, 80, 240))
    ]
    cards = []
    card_width = 190
    card_height = 80
    gap_x = 25
    gap_y = 20
    start_x = (WIDTH - (2 * card_width + gap_x)) // 2
    start_y = 120
    for idx, (label, value, color) in enumerate(levels):
        col = idx % 2
        row = idx // 2
        x = start_x + col * (card_width + gap_x)
        y = start_y + row * (card_height + gap_y)
        cards.append((pygame.Rect(x, y, card_width, card_height), value, label, color))
    custom_box = pygame.Rect((WIDTH - 200) // 2, 450, 200, 60)
    start_btn = pygame.Rect((WIDTH - 160) // 2, 540, 160, 50)
    input_text = ""
    error_msg = ""
    custom_active = False
    while True:
        screen.fill((40, 40, 45))
        title = menu_font.render("Select AI Elo Rating", True, (255, 255, 255))
        back_btn = draw_back_button()
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 50)))
        for rect, val, name, color in cards:
            pygame.draw.rect(screen, color, rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=8)
            n_surf = small_menu_font.render(name, True, (20, 20, 20))
            e_surf = small_menu_font.render(f"{val} ELO", True, (20, 20, 20))
            screen.blit(n_surf, n_surf.get_rect(center=(rect.centerx, rect.centery - 15)))
            screen.blit(e_surf, e_surf.get_rect(center=(rect.centerx, rect.centery + 15)))
        custom_lbl = small_menu_font.render("Or Enter Custom ELO (1 - 3000):", True, (200, 200, 200))
        screen.blit(custom_lbl, custom_lbl.get_rect(center=(WIDTH // 2, 430)))
        bg_color = (30, 30, 35) if not custom_active else (50, 50, 55)
        border_color = (120, 120, 120) if not custom_active else (80, 200, 120)
        pygame.draw.rect(screen, bg_color, custom_box, border_radius=8)
        pygame.draw.rect(screen, border_color, custom_box, 2, border_radius=8)
        typed_surf = input_font.render(input_text, True, (255, 255, 255))
        screen.blit(typed_surf, typed_surf.get_rect(center=custom_box.center))
        pygame.draw.rect(screen, (80, 180, 100), start_btn, border_radius=8)
        btn_text = small_menu_font.render("NEXT", True, (255, 255, 255))
        screen.blit(btn_text, btn_text.get_rect(center=start_btn.center))
        if error_msg:
            err_surf = coord_font.render(error_msg, True, (255, 100, 100))
            screen.blit(err_surf, err_surf.get_rect(center=(WIDTH // 2, 522)))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if back_btn.collidepoint(pos):
                    return "BACK"
                for rect, val, _, _ in cards:
                    if rect.collidepoint(pos):
                        return val
                if custom_box.collidepoint(pos):
                    custom_active = True
                    error_msg = ""
                else:
                    custom_active = False
                if start_btn.collidepoint(pos):
                    if input_text.isdigit():
                        val = int(input_text)
                        if 1 <= val <= 3000:
                            return val
                        else:
                            error_msg = "Must be between 1 and 3000!"
                    else:
                        error_msg = "Please type a valid ELO!"
            if event.type == pygame.KEYDOWN and custom_active:
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_RETURN:
                    if input_text.isdigit():
                        val = int(input_text)
                        if 1 <= val <= 3000:
                            return val
                        else:
                            error_msg = "Must be between 1 and 3000!"
                    else:
                        error_msg = "Please type a valid ELO!"
                else:
                    if len(input_text) < 4 and event.unicode.isdigit():
                        input_text += event.unicode
                        error_msg = ""

def select_depth():
    input_text = ""
    input_box = pygame.Rect((WIDTH - 200) // 2, 280, 200, 80)
    btn_rect = pygame.Rect((WIDTH - 180) // 2, 420, 180, 60)
    error_msg = ""
    while True:
        screen.fill((50, 50, 50))
        title_text = menu_font.render("Set AI Search Depth", True, (255, 255, 255))
        back_btn = draw_back_button()
        screen.blit(title_text, title_text.get_rect(center=(WIDTH // 2, 100)))
        hint_text = pygame.font.SysFont("arial", 20).render("Enter look-ahead limit (1 to 32)", True, (200, 200, 200))
        screen.blit(hint_text, hint_text.get_rect(center=(WIDTH // 2, 150)))
        warning_text = pygame.font.SysFont("arial", 16).render("(Depths above 4 will cause extreme computation delays)", True, (180, 100, 100))
        screen.blit(warning_text, warning_text.get_rect(center=(WIDTH // 2, 185)))
        pygame.draw.rect(screen, (30, 30, 30), input_box, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), input_box, 3, border_radius=10)
        typed_surf = input_font.render(input_text, True, (255, 255, 255))
        screen.blit(typed_surf, typed_surf.get_rect(center=input_box.center))
        pygame.draw.rect(screen, (80, 180, 100), btn_rect, border_radius=8)
        btn_text = pygame.font.SysFont("arial", 24, bold=True).render("START GAME", True, (255, 255, 255))
        screen.blit(btn_text, btn_text.get_rect(center=btn_rect.center))
        if error_msg:
            err_surf = pygame.font.SysFont("arial", 18, bold=True).render(error_msg, True, (255, 100, 100))
            screen.blit(err_surf, err_surf.get_rect(center=(WIDTH // 2, 385)))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_RETURN:
                    if input_text.isdigit():
                        val = int(input_text)
                        if 1 <= val <= 32:
                            return val
                        else:
                            error_msg = "Please enter a value between 1 and 32"
                    else:
                        error_msg = "Please enter a valid number"
                else:
                    if len(input_text) < 2 and event.unicode.isdigit():
                        input_text += event.unicode
                        error_msg = ""
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if back_btn.collidepoint(pos):
                    return "BACK"
                if btn_rect.collidepoint(pos):
                    if input_text.isdigit():
                        val = int(input_text)
                        if 1 <= val <= 32:
                            return val
                        else:
                            error_msg = "Please enter a value between 1 and 32"
                    else:
                        error_msg = "Please enter a valid number"

def get_promotion_choice(color):
    options = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    symbols = ["♛", "♜", "♝", "♞"] if color == chess.BLACK else ["♕", "♖", "♗", "♘"]
    box_width, box_height = 400, 120
    popup_rect = pygame.Rect((BOARD_SIZE - box_width) // 2, (BOARD_SIZE - box_height) // 2, box_width, box_height)
    buttons = []
    for i in range(4):
        btn_x = popup_rect.x + 20 + i * 90
        btn_y = popup_rect.y + 20
        buttons.append(pygame.Rect(btn_x, btn_y, 80, 80))
    while True:
        pygame.draw.rect(screen, (200, 200, 200), popup_rect, border_radius=10)
        pygame.draw.rect(screen, (50, 50, 50), popup_rect, 4, border_radius=10)
        for i, rect in enumerate(buttons):
            pygame.draw.rect(screen, (240, 240, 240), rect, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 100), rect, 2, border_radius=5)
            sym_text = font.render(symbols[i], True, (0, 0, 0))
            sym_rect = sym_text.get_rect(center=rect.center)
            screen.blit(sym_text, sym_rect)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                for i, rect in enumerate(buttons):
                    if rect.collidepoint(pos):
                        return options[i]

def display_game_over(message):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    text = game_over_font.render(message, True, (255, 255, 255))
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text, rect)
    pygame.display.flip()
    pygame.time.wait(3000)

while True:
    game_mode = select_game_mode()

    if game_mode == "local":
        player = chess.WHITE
        selected_elo = 1500
        selected_depth = 3
        break

    player = select_color()
    if player == "BACK":
        continue

    selected_elo = select_difficulty()
    if selected_elo == "BACK":
        continue

    selected_depth = select_depth()
    if selected_depth == "BACK":
        continue

    break

selected = None
running = True

if player == chess.BLACK:
    bot_move = smart_move(board, selected_elo, selected_depth)
    if bot_move:
        play_move_sound(board, bot_move)
        board.push(bot_move)

while running:
    current_evaluation = evaluate_board(board)
    draw_board()
    draw_coordinates()
    draw_pieces()
    draw_legal_destinations(selected)
    draw_evaluation_bar(current_evaluation)
    draw_feedback()
    undo_button = draw_controls()
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if undo_button.collidepoint(pos):
                if game_mode == "bot" and len(board.move_stack) >= 2:
                    board.pop()
                    board.pop()
                elif game_mode == "local" and len(board.move_stack) >= 1:
                    board.pop()
                    player = chess.WHITE if board.turn == chess.WHITE else chess.BLACK
                selected = None
                continue
            if pos[0] < BOARD_SIZE and pos[1] < BOARD_SIZE:
                col = pos[0] // SQUARE
                row = pos[1] // SQUARE
                if player == chess.WHITE:
                    clicked_square = chess.square(col, 7 - row)
                else:
                    clicked_square = chess.square(7 - col, row)
                
                if selected is None:
                    piece = board.piece_at(clicked_square)
                    if piece and piece.color == board.turn:
                        selected = clicked_square
                else:
                    move = chess.Move(selected, clicked_square)
                    pawn_piece = board.piece_at(selected)
                    if pawn_piece and pawn_piece.piece_type == chess.PAWN:
                        to_rank = chess.square_rank(clicked_square)
                        if (pawn_piece.color == chess.WHITE and to_rank == 7) or \
                           (pawn_piece.color == chess.BLACK and to_rank == 0):
                            promo_piece = get_promotion_choice(pawn_piece.color)
                            move = chess.Move(selected, clicked_square, promotion=promo_piece)
                    
                    if move in board.legal_moves:
                        play_move_sound(board, move)
                        quality = get_move_quality(board, move, selected_depth)
                        last_move_feedback = (move.uci(), quality[1], quality[2], pygame.time.get_ticks())
                        board.push(move)
                        selected = None
                        
                        if game_mode == "local":
                            player = chess.WHITE if board.turn == chess.WHITE else chess.BLACK
                        elif game_mode == "bot" and not board.is_game_over():
                            draw_board()
                            draw_coordinates()
                            draw_pieces()
                            pygame.display.flip()
                            bot_move = smart_move(board, selected_elo, selected_depth)
                            if bot_move:
                                play_move_sound(board, bot_move)
                                board.push(bot_move)
                    else:
                        piece = board.piece_at(clicked_square)
                        if piece and piece.color == board.turn:
                            selected = clicked_square
                        else:
                            selected = None
                            
    if board.is_game_over():
        outcome_text = "Game Over!"
        if board.is_checkmate():
            winner = "Black" if board.turn == chess.WHITE else "White"
            outcome_text = f"Checkmate! {winner} wins!"
        elif board.is_stalemate():
            outcome_text = "Draw by Stalemate!"
        elif board.is_insufficient_material():
            outcome_text = "Draw by Insufficient Material!"
        display_game_over(outcome_text)
        running = False

pygame.quit()
sys.exit()
