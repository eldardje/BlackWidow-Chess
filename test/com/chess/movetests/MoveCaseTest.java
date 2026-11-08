package com.chess.movetests;

import com.chess.engine.board.Board;
import com.chess.engine.board.MoveTransition;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.runners.Parameterized;
import org.junit.runners.Parameterized.Parameters;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertEquals;

/** Runs the 416 input-domain cases listed in the Step 2 design document. */
@RunWith(Parameterized.class)
public class MoveCaseTest {

    private final Map<String, String> row;

    public MoveCaseTest(final String id, final Map<String, String> row) {
        this.row = row;
    }

    @Parameters(name = "{0}")
    public static Collection<Object[]> cases() {
        final List<Object[]> cases = new ArrayList<>();
        for (final Map<String, String> row : MoveTestSupport.readCsv("move_cases.csv")) {
            cases.add(new Object[]{row.get("id"), row});
        }
        return cases;
    }

    @Test
    public void moveHasExpectedOutcome() {
        final Board board = MoveTestSupport.load(row.get("fen"), row.get("setup"));
        final MoveTransition transition = MoveTestSupport.attempt(
                board, row.get("from"), row.get("to"), row.get("promotion"));
        final boolean expectLegal = "LEGAL".equals(row.get("expected"));
        assertEquals(row.get("rationale") + " [" + row.get("blocks") + "], engine status "
                + transition.getMoveStatus(), expectLegal, transition.getMoveStatus().isDone());
        if (expectLegal) {
            assertEquals("Wrong board after the move", row.get("after"),
                    MoveTestSupport.placementAndTurn(transition.getToBoard()));
        }
    }
}
