#!/usr/bin/env python3
"""Generates the BlackWidow move-legality test data from the input domain model.

Expected results come from python-chess, an independent implementation of the
FIDE rules, never from the engine under test. Every case is written for White
and then mirrored, so each one also exists for Black.

    pip install chess
    python tools/movetests/gen_move_cases.py test/data/movetests
"""
import csv, os, random, sys
import chess

LOCATIONS = {"corner": chess.A1, "edge": chess.A4, "interior": chess.D4}
PIECES = {"K": chess.KING, "Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}
TARGETS = ["empty", "enemy", "own", "off_pattern", "past_piece"]
ORACLE_RECORDS = []


def between_mid(a, b):
    """Square halfway between two squares on one line, or None."""
    fa, ra, fb, rb = chess.square_file(a), chess.square_rank(a), chess.square_file(b), chess.square_rank(b)
    if (fa + fb) % 2 or (ra + rb) % 2:
        return None
    return chess.square((fa + fb) // 2, (ra + rb) // 2)


def attacks_on_empty(piece_type, sq):
    b = chess.Board(None)
    b.set_piece_at(sq, chess.Piece(piece_type, chess.WHITE))
    return set(b.attacks(sq))


def pick_on_pattern(piece_type, sq, distance):
    options = [t for t in sorted(attacks_on_empty(piece_type, sq))
               if chess.square_distance(sq, t) == distance]
    return options[len(options) // 2]


def build_model_a(letter, loc_name, target_kind):
    """Model A: all combinations of piece x location x target relation."""
    pt = PIECES[letter]
    sq = LOCATIONS[loc_name]
    slider = pt in (chess.QUEEN, chess.ROOK, chess.BISHOP)
    b = chess.Board(None)
    b.set_piece_at(sq, chess.Piece(pt, chess.WHITE))
    if target_kind == "off_pattern":
        reach = attacks_on_empty(pt, sq)
        to = next(t for t in [chess.F6, chess.E6, chess.G3, chess.C6, chess.B5, chess.F3, chess.C3]
                  if t not in reach and t != sq)
    elif target_kind == "past_piece":
        if pt == chess.KNIGHT:
            to = pick_on_pattern(pt, sq, 2)
            df = 1 if chess.square_file(to) > chess.square_file(sq) else -1
            dr = 1 if chess.square_rank(to) > chess.square_rank(sq) else -1
            b.set_piece_at(chess.square(chess.square_file(sq) + df, chess.square_rank(sq)), chess.Piece(chess.KNIGHT, chess.WHITE))
            b.set_piece_at(chess.square(chess.square_file(sq), chess.square_rank(sq) + dr), chess.Piece(chess.KNIGHT, chess.BLACK))
        else:
            to = pick_on_pattern(chess.QUEEN if pt == chess.KING else pt, sq, 2)
            b.set_piece_at(between_mid(sq, to), chess.Piece(chess.KNIGHT, chess.BLACK))
    else:
        to = pick_on_pattern(pt, sq, 2 if slider or pt == chess.KNIGHT else 1)
        if target_kind == "enemy":
            b.set_piece_at(to, chess.Piece(chess.KNIGHT, chess.BLACK))
        elif target_kind == "own":
            b.set_piece_at(to, chess.Piece(chess.KNIGHT, chess.WHITE))
    want_legal = target_kind in ("empty", "enemy") or (target_kind == "past_piece" and pt == chess.KNIGHT)
    return place_kings(b, chess.Move(sq, to), pt, want_legal)


def place_kings(b, move, pt, want_legal):
    """Add the missing kings on quiet squares that keep the expected outcome."""
    for wk in ([None] if pt == chess.KING else [chess.H1, chess.G1, chess.H2, chess.F1, chess.E1, chess.G2]):
        for bk in [chess.H8, chess.G8, chess.H7, chess.F8, chess.E8, chess.G7, chess.A8, chess.B8]:
            c = b.copy()
            if wk is not None:
                if c.piece_at(wk) or wk in (move.from_square, move.to_square):
                    continue
                c.set_piece_at(wk, chess.Piece(chess.KING, chess.WHITE))
            if c.piece_at(bk) or bk == move.to_square:
                continue
            c.set_piece_at(bk, chess.Piece(chess.KING, chess.BLACK))
            c.turn = chess.WHITE
            c.castling_rights = 0
            if c.is_valid() and not c.is_check() and c.is_legal(move) == want_legal:
                return c.fen(), move.uci()
    raise RuntimeError(f"no king placement for {b.fen()} {move}")


def model_a():
    n = 0
    for letter in PIECES:
        for loc in LOCATIONS:
            for t in TARGETS:
                n += 1
                fen, uci = build_model_a(letter, loc, t)
                yield (f"A{n:02d}", "A-Piece", f"piece={letter};location={loc};target={t}", fen, "", uci,
                       f"{letter} from {loc} to {t} target")


def table(prefix, model, rows):
    for i, (blocks, fen, setup, uci, why) in enumerate(rows, 1):
        yield (f"{prefix}{i:02d}", model, blocks, fen, setup, uci, why)


K = "4k3/8/8/8/8/8/8/4K3"
PAWN_ROWS = [
    ("rank=start;action=single;occupancy=clear", "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", "", "e2e3", "single step from start"),
    ("rank=start;action=double;occupancy=clear", "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", "", "e2e4", "double step from start"),
    ("rank=mid;action=double;occupancy=clear", "4k3/8/8/8/8/4P3/8/4K3 w - - 0 1", "", "e3e5", "double step off start rank"),
    ("rank=mid;action=double;occupancy=history", "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", "e2e3 e8d8", "e3e5", "second double step after moving"),
    ("rank=mid;action=triple;occupancy=clear", "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1", "", "e2e5", "three squares forward"),
    ("rank=mid;action=single;occupancy=clear", "4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", "", "e4e5", "base: single step mid board"),
    ("rank=mid;action=backward;occupancy=clear", "4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", "", "e4e3", "backward"),
    ("rank=mid;action=sideways;occupancy=clear", "4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", "", "e4d4", "sideways"),
    ("rank=mid;action=diagonal;occupancy=empty", "4k3/8/8/8/4P3/8/8/4K3 w - - 0 1", "", "e4d5", "diagonal with nothing to capture"),
    ("rank=mid;action=diagonal;occupancy=enemy", "4k3/8/8/3n4/4P3/8/8/4K3 w - - 0 1", "", "e4d5", "capture toward a file"),
    ("rank=mid;action=diagonal;occupancy=enemy", "4k3/8/8/5n2/4P3/8/8/4K3 w - - 0 1", "", "e4f5", "capture toward h file"),
    ("rank=mid;action=diagonal;occupancy=own", "4k3/8/8/3N4/4P3/8/8/4K3 w - - 0 1", "", "e4d5", "diagonal onto own piece"),
    ("rank=mid;action=single;occupancy=enemy", "4k3/8/8/4n3/4P3/8/8/4K3 w - - 0 1", "", "e4e5", "forward capture is not allowed"),
    ("rank=mid;action=single;occupancy=own", "4k3/8/8/4N3/4P3/8/8/4K3 w - - 0 1", "", "e4e5", "blocked by own piece"),
    ("rank=start;action=double;occupancy=near_blocked", "4k3/8/8/8/8/4n3/4P3/4K3 w - - 0 1", "", "e2e4", "cannot jump a piece on e3"),
    ("rank=start;action=double;occupancy=far_blocked", "4k3/8/8/8/4n3/8/4P3/4K3 w - - 0 1", "", "e2e4", "double step onto occupied e4"),
    ("rank=start;action=wide;occupancy=enemy", "4k3/8/8/8/6n1/8/4P3/4K3 w - - 0 1", "", "e2g4", "two square diagonal"),
    ("rank=mid;file=a;action=diagonal;occupancy=enemy", "4k3/8/8/1n6/P7/8/8/4K3 w - - 0 1", "", "a4b5", "capture from a file"),
    ("rank=mid;file=h;action=diagonal;occupancy=enemy", "4k3/8/8/6n1/7P/8/8/4K3 w - - 0 1", "", "h4g5", "capture from h file"),
]
PROMO_FEN = {"push": ("8/4P2k/8/8/8/8/8/4K3 w - - 0 1", "e7e8"),
             "capture_a_side": ("3n4/4P2k/8/8/8/8/8/4K3 w - - 0 1", "e7d8"),
             "capture_h_side": ("5n2/4P2k/8/8/8/8/8/4K3 w - - 0 1", "e7f8")}
PROMO_EXTRA = [
    ("path=blocked_enemy;piece=q", "4n3/4P2k/8/8/8/8/8/4K3 w - - 0 1", "", "e7e8q", "promotion square occupied by enemy"),
    ("path=blocked_own;piece=q", "4R3/4P2k/8/8/8/8/8/4K3 w - - 0 1", "", "e7e8q", "promotion square occupied by own piece"),
    ("path=diagonal_empty;piece=q", "8/4P2k/8/8/8/8/8/4K3 w - - 0 1", "", "e7d8q", "diagonal promotion with no capture"),
    ("path=push;piece=k", "8/4P2k/8/8/8/8/8/4K3 w - - 0 1", "", "e7e8k", "promotion to a king"),
    ("path=push;piece=p", "8/4P2k/8/8/8/8/8/4K3 w - - 0 1", "", "e7e8p", "promotion to a pawn"),
]
C = "4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1"
def castle_rows(wing, uci, rook_sq, path_sq, transit, dest, other_rights):
    q = wing == "queen"
    def fen(extra):  # extra: {square: piece letter}
        b = chess.Board(C)
        for s, p in extra.items():
            b.set_piece_at(chess.parse_square(s), chess.Piece.from_symbol(p))
        return b.fen()
    w = f"wing={wing};"
    return [
        (w + "condition=base", C, "", uci, "base: all castling conditions met"),
        (w + "condition=own_piece_between", fen({path_sq: "N"}), "", uci, "own piece between king and rook"),
        (w + "condition=enemy_piece_between", fen({path_sq: "n"}), "", uci, "enemy piece between king and rook"),
        (w + "condition=king_moved_back", C, "e1d1 e8d8 d1e1 d8e8", uci, "king moved and returned"),
        (w + "condition=rook_moved_back", C, f"{rook_sq}{'b1' if q else 'g1'} e8d8 {'b1' if q else 'g1'}{rook_sq} d8e8", uci, "rook moved and returned"),
        (w + "condition=other_rook_moved", C, f"{'h1g1' if q else 'a1b1'} e8d8 {'g1h1' if q else 'b1a1'} d8e8", uci, "only the other rook moved"),
        (w + "condition=rook_missing", chess.Board(C).fen().replace("R3K2R", "4K2R" if q else "R3K3").replace(" KQ ", " K " if q else " Q "), "", uci, "rook is gone"),
        (w + "condition=right_absent_in_fen", C.replace(" KQ ", " " + other_rights + " "), "", uci, "FEN withholds this wing right only"),
        (w + "condition=no_rights_in_fen", C.replace(" KQ ", " - "), "", uci, "FEN withholds both rights"),
        (w + "condition=king_in_check", "4k3/8/8/4r3/8/8/8/R3K2R w KQ - 0 1", "", uci, "castling out of check"),
        (w + "condition=transit_attacked", f"4k3/8/8/{'3r4' if q else '5r2'}/8/8/8/R3K2R w KQ - 0 1", "", uci, "king crosses an attacked square"),
        (w + "condition=destination_attacked", f"4k3/8/8/{'2r5' if q else '6r1'}/8/8/8/R3K2R w KQ - 0 1", "", uci, "king lands on an attacked square"),
        (w + "condition=transit_attacked_by_pawn", f"4k3/8/8/8/8/8/{'2p5' if q else '6p1'}/R3K2R w KQ - 0 1", "", uci, "pawn covers the crossing square"),
        (w + "condition=destination_attacked_by_pawn", f"4k3/8/8/8/8/8/{'1p6' if q else '7p'}/R3K2R w KQ - 0 1", "", uci, "pawn covers the landing square"),
        (w + "condition=enemy_pawn_on_e2", "4k3/8/8/8/8/8/4p3/R3K2R w KQ - 0 1", "", uci, "pawn on e2 covers d1 and f1"),
        (w + "condition=rook_attacked", f"4k3/8/8/{'r7' if q else '7r'}/8/8/8/R3K2R w KQ - 0 1", "", uci, "attacked rook may still castle"),
    ] + ([(w + "condition=b1_attacked", "4k3/8/8/1r6/8/8/8/R3K2R w KQ - 0 1", "", uci, "b1 may be attacked on the queen side")] if q else [])
PEP = "4k3/3p1p2/8/4P3/8/8/8/4K3 b - - 0 1"
EP_ROWS = [
    ("side=a_side;timing=immediate;condition=base", PEP, "d7d5", "e5d6", "base: capture toward a file"),
    ("side=h_side;timing=immediate;condition=base", PEP, "f7f5", "e5f6", "capture toward h file"),
    ("side=a_side;timing=one_move_late;condition=base", PEP, "d7d5 e1d1 e8d8", "e5d6", "right expires after one move"),
    ("side=a_side;timing=immediate;condition=single_step_pawn", "4k3/8/3p4/4P3/8/8/8/4K3 b - - 0 1", "d6d5", "e5d6", "enemy pawn only moved one square"),
    ("side=a_side;timing=immediate;condition=not_adjacent", "4k3/3p4/8/1P6/8/8/8/4K3 b - - 0 1", "d7d5", "b5c6", "capturing pawn is not beside it"),
    ("side=a_side;timing=immediate;condition=wrong_rank", "4k3/3p4/8/8/4P3/8/8/4K3 b - - 0 1", "d7d5 e4e5 e8d8", "e5d6", "capturer arrived after the jump"),
    ("side=a_edge;timing=immediate;condition=base", "4k3/1p6/8/P7/8/8/8/4K3 b - - 0 1", "b7b5", "a5b6", "capture from a file"),
    ("side=h_edge;timing=immediate;condition=base", "4k3/6p1/8/7P/8/8/8/4K3 b - - 0 1", "g7g5", "h5g6", "capture from h file"),
    ("side=a_side;timing=immediate;condition=pin_on_rank", "4k3/3p4/8/K3P2r/8/8/8/8 b - - 0 1", "d7d5", "e5d6", "both pawns leave the rank and expose the king"),
    ("side=a_side;timing=immediate;condition=pin_leaves_diagonal", "4k2K/3p4/8/4P3/8/8/8/b7 b - - 0 1", "d7d5", "e5d6", "capturing pawn is pinned on a diagonal"),
    ("side=a_side;timing=immediate;condition=pin_stays_on_diagonal", "1b2k3/3p4/8/4P3/8/8/7K/8 b - - 0 1", "d7d5", "e5d6", "capture stays on the pinning diagonal"),
    ("side=a_side;timing=immediate;condition=resolves_check", "4k3/3p4/8/4P3/4K3/8/8/8 b - - 0 1", "d7d5", "e5d6", "capture removes the checking pawn"),
    ("side=a_side;timing=fen;condition=fen_square_given", "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "", "e5d6", "en passant square supplied by FEN"),
    ("side=a_side;timing=fen;condition=fen_square_absent", "4k3/8/8/3pP3/8/8/8/4K3 w - - 0 1", "", "e5d6", "no en passant square in FEN"),
]
SAFETY_ROWS = [
    ("mover=K;state=not_in_check;result=enters_attack", "4r2k/8/8/8/8/8/8/3K4 w - - 0 1", "", "d1e1", "into a rook file"),
    ("mover=K;state=not_in_check;result=beside_enemy_king", "8/8/8/3k4/8/3K4/8/8 w - - 0 1", "", "d3d4", "next to the enemy king"),
    ("mover=K;state=not_in_check;result=pawn_attack", "7k/8/8/4p3/8/3K4/8/8 w - - 0 1", "", "d3d4", "onto a pawn attacked empty square"),
    ("mover=K;state=not_in_check;result=in_front_of_pawn", "7k/8/8/4p3/8/4K3/8/8 w - - 0 1", "", "e3e4", "square a pawn only pushes to is safe"),
    ("mover=K;state=not_in_check;result=captures_guarded", "3r3k/8/8/8/3n4/3K4/8/8 w - - 0 1", "", "d3d4", "captures a defended piece"),
    ("mover=K;state=not_in_check;result=captures_loose", "7k/8/8/8/3n4/3K4/8/8 w - - 0 1", "", "d3d4", "captures an undefended piece"),
    ("mover=K;state=in_check;result=retreats_on_ray", "4r2k/8/8/8/4K3/8/8/8 w - - 0 1", "", "e4e3", "stays on the checking line"),
    ("mover=K;state=in_check;result=steps_off_ray", "4r2k/8/8/8/4K3/8/8/8 w - - 0 1", "", "e4d4", "steps out of check"),
    ("mover=R;state=pinned_file;result=along_pin", "4r2k/8/8/8/8/4R3/8/4K3 w - - 0 1", "", "e3e5", "pinned rook slides on the pin"),
    ("mover=R;state=pinned_file;result=captures_pinner", "4r2k/8/8/8/8/4R3/8/4K3 w - - 0 1", "", "e3e8", "pinned rook captures the pinner"),
    ("mover=R;state=pinned_file;result=off_pin", "4r2k/8/8/8/8/4R3/8/4K3 w - - 0 1", "", "e3a3", "pinned rook leaves the pin"),
    ("mover=B;state=pinned_diagonal;result=along_pin", "7k/8/8/7b/8/5B2/8/3K4 w - - 0 1", "", "f3g4", "pinned bishop slides on the pin"),
    ("mover=B;state=pinned_diagonal;result=off_pin", "7k/8/8/7b/8/5B2/8/3K4 w - - 0 1", "", "f3e4", "pinned bishop leaves the pin"),
    ("mover=B;state=pinned_file;result=off_pin", "4r2k/8/8/8/8/4B3/8/4K3 w - - 0 1", "", "e3d4", "bishop pinned on a file cannot move"),
    ("mover=Q;state=pinned_file;result=along_pin", "4r2k/8/8/8/8/4Q3/8/4K3 w - - 0 1", "", "e3e6", "pinned queen slides on the pin"),
    ("mover=Q;state=pinned_file;result=off_pin", "4r2k/8/8/8/8/4Q3/8/4K3 w - - 0 1", "", "e3d3", "pinned queen leaves the pin"),
    ("mover=N;state=pinned_file;result=off_pin", "4r2k/8/8/8/8/4N3/8/4K3 w - - 0 1", "", "e3c4", "pinned knight cannot move"),
    ("mover=P;state=pinned_file;result=along_pin", "4r2k/8/8/8/8/4P3/8/4K3 w - - 0 1", "", "e3e4", "pawn pushes along a file pin"),
    ("mover=P;state=pinned_rank;result=off_pin", "7k/8/8/8/8/8/K3P2r/8 w - - 0 1", "", "e2e3", "pawn pinned on a rank cannot push"),
    ("mover=P;state=pinned_diagonal;result=captures_pinner", "7k/8/8/8/8/5b2/4P3/3K4 w - - 0 1", "", "e2f3", "pinned pawn captures the pinner"),
    ("mover=P;state=pinned_diagonal;result=off_pin", "7k/8/8/8/8/5b2/4P3/3K4 w - - 0 1", "", "e2e3", "pinned pawn leaves the pin"),
    ("mover=R;state=in_check;result=blocks", "4r2k/8/8/8/8/R7/8/4K3 w - - 0 1", "", "a3e3", "interposes"),
    ("mover=N;state=in_check;result=captures_checker", "4r2k/8/3N4/8/8/8/8/4K3 w - - 0 1", "", "d6e8", "captures the checking piece"),
    ("mover=R;state=in_check;result=ignores_check", "4r2k/8/8/8/8/R7/8/4K3 w - - 0 1", "", "a3a4", "unrelated move while in check"),
    ("mover=P;state=in_check;result=blocks", "7k/8/8/1b6/8/8/3P4/5K2 w - - 0 1", "", "d2d3", "pawn push blocks a diagonal check"),
    ("mover=R;state=double_check;result=blocks_one", "4r2k/8/8/8/8/3n4/R7/4K3 w - - 0 1", "", "a2e2", "one block cannot stop two checkers"),
    ("mover=R;state=double_check;result=captures_one", "4r2k/8/8/8/8/R2n4/8/4K3 w - - 0 1", "", "a3d3", "one capture cannot stop two checkers"),
    ("mover=K;state=double_check;result=steps_away", "4r2k/8/8/8/8/3n4/8/4K3 w - - 0 1", "", "e1d2", "only the king can answer a double check"),
]
WRAP_ROWS = [
    ("piece=R;edge=h;step=+1", "6k1/8/8/8/7R/8/8/K7 w - - 0 1", "", "h4a3", "coordinate +1 from h4 wraps to a3"),
    ("piece=R;edge=a;step=-1", "7k/8/8/8/R7/8/8/7K w - - 0 1", "", "a4h5", "coordinate -1 from a4 wraps to h5"),
    ("piece=Q;edge=h;step=+1", "6k1/8/8/8/7Q/8/8/K7 w - - 0 1", "", "h4a3", "queen wrap on +1"),
    ("piece=Q;edge=a;step=-1", "7k/8/8/8/Q7/8/8/7K w - - 0 1", "", "a4h5", "queen wrap on -1"),
    ("piece=Q;edge=h;step=+9", "6k1/8/8/8/7Q/8/8/K7 w - - 0 1", "", "h4a2", "queen wrap on +9"),
    ("piece=Q;edge=a;step=-9", "7k/8/8/8/Q7/8/8/7K w - - 0 1", "", "a4h6", "queen wrap on -9"),
    ("piece=B;edge=h;step=-7", "6k1/8/8/8/7B/8/8/K7 w - - 0 1", "", "h4a4", "bishop wrap on -7"),
    ("piece=B;edge=h;step=+9", "6k1/8/8/8/7B/8/8/K7 w - - 0 1", "", "h4a2", "bishop wrap on +9"),
    ("piece=B;edge=a;step=-9", "7k/8/8/8/B7/8/8/7K w - - 0 1", "", "a4h6", "bishop wrap on -9"),
    ("piece=B;edge=a;step=+7", "7k/8/8/8/B7/8/8/7K w - - 0 1", "", "a4h4", "bishop wrap on +7"),
    ("piece=K;edge=h;step=+1", "k7/8/8/8/7K/8/8/8 w - - 0 1", "", "h4a3", "king wrap on +1"),
    ("piece=K;edge=a;step=-1", "7k/8/8/8/K7/8/8/8 w - - 0 1", "", "a4h5", "king wrap on -1"),
    ("piece=N;edge=h;step=+10", "k7/8/8/8/7N/8/8/K7 w - - 0 1", "", "h4b2", "knight wrap on +10"),
    ("piece=N;edge=g;step=+10", "k7/8/8/8/6N1/8/8/K7 w - - 0 1", "", "g4a2", "knight wrap from g file"),
    ("piece=N;edge=a;step=-10", "7k/8/8/8/N7/8/8/7K w - - 0 1", "", "a4g6", "knight wrap on -10"),
    ("piece=N;edge=b;step=-10", "7k/8/8/8/1N6/8/8/7K w - - 0 1", "", "b4h6", "knight wrap from b file"),
    ("piece=P;edge=a;step=-9", "4k3/8/7n/8/P7/8/8/4K3 w - - 0 1", "", "a4h6", "pawn capture wrap, a4 to h6"),
    ("piece=P;edge=h;step=-7", "4k3/8/8/8/n6P/8/8/4K3 w - - 0 1", "", "h4a4", "pawn capture wrap, h4 to a4"),
]
SELECT_ROWS = [
    ("selection=empty_square", "4k3/8/8/8/8/8/8/4K2R w K - 0 1", "", "d4d5", "nothing on the source square"),
    ("selection=opponent_piece", "4k2r/8/8/8/8/8/8/4K2R w - - 0 1", "", "h8h7", "opponent's rook on White's turn"),
    ("selection=same_square", "4k3/8/8/8/8/8/8/4K2R w - - 0 1", "", "h1h1", "source equals destination"),
    ("selection=out_of_turn", "7k/8/8/8/8/8/8/K6R b - - 0 1", "", "h1h8", "White rook move on Black's turn"),
]


def all_cases():
    yield from model_a()
    yield from table("P", "B-Pawn", PAWN_ROWS)
    rows = []
    for path, (fen, uci) in PROMO_FEN.items():
        for p in "qrbn":
            rows.append((f"path={path};piece={p}", fen, "", uci + p, f"{path} promotes to {p}"))
    yield from table("F", "C-Promotion", rows + PROMO_EXTRA)
    yield from table("C", "D-Castling",
                     castle_rows("king", "e1g1", "h1", "f1", "f1", "g1", "Q") +
                     castle_rows("queen", "e1c1", "a1", "d1", "d1", "c1", "K") )
    yield from table("E", "E-EnPassant", EP_ROWS)
    yield from table("S", "F-KingSafety", SAFETY_ROWS)
    yield from table("W", "G-BoardEdge", WRAP_ROWS)
    yield from table("X", "H-Selection", SELECT_ROWS)


def replay(fen, setup):
    b = chess.Board(fen)
    for m in setup.split():
        mv = chess.Move.from_uci(m)
        assert b.is_legal(mv), (fen, setup, m)
        b.push(mv)
    return b


def is_legal(b, uci):
    mv = chess.Move(chess.parse_square(uci[:2]), chess.parse_square(uci[2:4]))
    if len(uci) == 5:
        mv.promotion = chess.Piece.from_symbol(uci[4]).piece_type
        if mv.promotion in (chess.KING, chess.PAWN):
            return False, mv
    return mv != chess.Move(mv.from_square, mv.from_square) and b.is_legal(mv), mv


def key(b):
    parts = b.fen(en_passant="fen").split()
    return " ".join(parts[:2])


def mirror_uci(u):
    return "".join(chess.square_name(chess.square_mirror(chess.parse_square(u[i:i+2]))) for i in (0, 2)) + u[4:]


def emit(case, side):
    cid, model, blocks, fen, setup, uci, why = case
    b0 = chess.Board(fen)
    assert b0.is_valid(), (cid, fen, b0.status())
    if side == "B":
        fen = b0.mirror().fen()
        setup = " ".join(mirror_uci(m) for m in setup.split())
        uci = mirror_uci(uci)
    b = replay(fen, setup)
    legal, mv = is_legal(b, uci)
    after = ""
    if legal:
        c = b.copy()
        c.push(mv)
        after = key(c)
    return [f"{cid}{side}", model, blocks + f";side={side}", fen, setup, uci[:2], uci[2:4], uci[4:],
            "LEGAL" if legal else "ILLEGAL", after, why], b


def main(out):
    os.makedirs(out, exist_ok=True)
    head = ["id", "model", "blocks", "fen", "setup", "from", "to", "promotion", "expected", "after", "rationale"]
    sets = {}
    with open(os.path.join(out, "move_cases.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(head)
        for case in all_cases():
            for side in "WB":
                row, b = emit(case, side)
                w.writerow(row)
                sets[(row[3], row[4])] = " ".join(sorted(m.uci() for m in b.legal_moves))
    with open(os.path.join(out, "position_sets.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["fen", "setup", "legal_moves"])
        for (fen, setup), moves in sorted(sets.items()):
            w.writerow([fen, setup, moves])
    rng = random.Random(881)
    with open(os.path.join(out, "random_games.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["game", "ply", "move", "legal_moves"])
        for g in range(40):
            b = chess.Board()
            ply = 0
            while not b.is_game_over(claim_draw=False) and ply < 160:
                moves = sorted(m.uci() for m in b.legal_moves)
                mv = rng.choice(moves)
                w.writerow([g, ply, mv, " ".join(moves)])
                b.push_uci(mv)
                ply += 1


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
