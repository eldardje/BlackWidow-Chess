package com.chess.movetests;

import com.chess.engine.board.Board;
import com.chess.engine.board.Move;
import com.chess.engine.board.Move.MoveFactory;
import com.chess.engine.board.MoveUtils;
import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertSame;

/** Cases X05 and X06: coordinates algebraic notation cannot express. */
public class OffBoardSelectionTest {

    private static void assertRejected(final int from, final int to) {
        final Board board = Board.createStandardBoard();
        final Move move = MoveFactory.createMove(board, from, to);
        assertSame(MoveUtils.NULL_MOVE, move);
        assertFalse(board.currentPlayer().makeMove(move).getMoveStatus().isDone());
    }

    @Test
    public void x05OffBoardSource() {
        assertRejected(-1, 16);
    }

    @Test
    public void x06OffBoardDestination() {
        assertRejected(48, 64);
    }
}
