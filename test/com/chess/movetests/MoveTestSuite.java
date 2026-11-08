package com.chess.movetests;

import org.junit.runner.RunWith;
import org.junit.runners.Suite;

@RunWith(Suite.class)
@Suite.SuiteClasses({MoveCaseTest.class,
                     OffBoardSelectionTest.class,
                     LegalMoveSetTest.class,
                     PerftTest.class})
public class MoveTestSuite {
}
