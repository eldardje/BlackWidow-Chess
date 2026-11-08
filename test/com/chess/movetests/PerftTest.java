package com.chess.movetests;

import com.chess.engine.board.Board;
import com.chess.engine.board.Move;
import com.chess.engine.board.MoveTransition;
import com.chess.pgn.FenUtilities;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

/** Counts every legal move sequence to a fixed depth against the published perft values. */
public class PerftTest {

    private static long perft(final Board board, final int depth) {
        if (depth == 0) {
            return 1;
        }
        long nodes = 0;
        for (final Move move : board.currentPlayer().getLegalMoves()) {
            final MoveTransition transition = board.currentPlayer().makeMove(move);
            if (transition.getMoveStatus().isDone()) {
                nodes += perft(transition.getToBoard(), depth - 1);
            }
        }
        return nodes;
    }

    private static void check(final String fen, final long... expected) {
        final Board board = FenUtilities.createGameFromFEN(fen);
        for (int depth = 1; depth <= expected.length; depth++) {
            assertEquals("depth " + depth, expected[depth - 1], perft(board, depth));
        }
    }

    @Test
    public void startPosition() {
        check("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 20, 400, 8902, 197281);
    }

    @Test
    public void kiwipete() {
        check("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 48, 2039, 97862);
    }

    @Test
    public void rookAndPawnEndgame() {
        check("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 14, 191, 2812, 43238);
    }

    @Test
    public void promotionsAndPins() {
        check("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 6, 264, 9467);
    }

    @Test
    public void castlingAndPromotionMix() {
        check("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 44, 1486, 62379);
    }

    @Test
    public void quietMiddlegame() {
        check("r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", 46, 2079, 89890);
    }
}
