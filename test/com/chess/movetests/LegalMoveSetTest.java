package com.chess.movetests;

import com.chess.engine.board.Board;
import org.junit.Test;

import java.util.Map;
import java.util.TreeSet;

import static org.junit.Assert.assertEquals;

/** Complete move-set checks: nothing extra and nothing missing, beyond the single move each case tries. */
public class LegalMoveSetTest {

    @Test
    public void everyDesignPositionMatchesTheOracle() {
        final StringBuilder failures = new StringBuilder();
        int count = 0;
        for (final Map<String, String> row : MoveTestSupport.readCsv("position_sets.csv")) {
            count++;
            final Board board = MoveTestSupport.load(row.get("fen"), row.get("setup"));
            compare(row.get("fen") + " after [" + row.get("setup") + "]",
                    MoveTestSupport.parseMoves(row.get("legal_moves")), MoveTestSupport.legalMoves(board), failures);
        }
        assertEquals(count + " positions compared\n" + failures, "", failures.toString());
    }

    @Test
    public void everyRandomGamePositionMatchesTheOracle() {
        final StringBuilder failures = new StringBuilder();
        String game = "";
        Board board = null;
        for (final Map<String, String> row : MoveTestSupport.readCsv("random_games.csv")) {
            if (!row.get("game").equals(game)) {
                game = row.get("game");
                board = Board.createStandardBoard();
            }
            compare("game " + game + " ply " + row.get("ply"),
                    MoveTestSupport.parseMoves(row.get("legal_moves")), MoveTestSupport.legalMoves(board), failures);
            board = MoveTestSupport.play(board, row.get("move"));
        }
        assertEquals(failures.toString(), "", failures.toString());
    }

    private static void compare(final String where, final TreeSet<String> expected,
                                final TreeSet<String> actual, final StringBuilder failures) {
        if (!expected.equals(actual)) {
            final TreeSet<String> missing = new TreeSet<>(expected);
            missing.removeAll(actual);
            final TreeSet<String> extra = new TreeSet<>(actual);
            extra.removeAll(expected);
            failures.append(where).append(": missing ").append(missing).append(", extra ").append(extra).append('\n');
        }
    }
}
