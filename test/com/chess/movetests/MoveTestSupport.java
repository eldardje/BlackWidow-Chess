package com.chess.movetests;

import com.chess.engine.board.Board;
import com.chess.engine.board.BoardUtils;
import com.chess.engine.board.Move;
import com.chess.engine.board.Move.MoveFactory;
import com.chess.engine.board.MoveTransition;
import com.chess.engine.pieces.Piece;
import com.chess.pgn.FenUtilities;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.LinkedHashMap;

/** Shared helpers: load positions, attempt moves, and read the test data files. */
final class MoveTestSupport {

    private static final Path DATA_DIR = Paths.get(System.getProperty("movetests.data", "test/data/movetests"));

    private MoveTestSupport() {
    }

    static int square(final String name) {
        return BoardUtils.INSTANCE.getCoordinateAtPosition(name);
    }

    static Board load(final String fen, final String setup) {
        Board board = FenUtilities.createGameFromFEN(fen);
        if (!setup.isEmpty()) {
            for (final String uci : setup.split(" ")) {
                board = play(board, uci);
            }
        }
        return board;
    }

    /** Plays a move that must be accepted, used for setup and game replay. */
    static Board play(final Board board, final String uci) {
        final MoveTransition transition = attempt(board, uci.substring(0, 2), uci.substring(2, 4), uci.substring(4));
        if (!transition.getMoveStatus().isDone()) {
            throw new IllegalStateException("Engine refused required move " + uci + ": " + transition.getMoveStatus());
        }
        return transition.getToBoard();
    }

    /** A move attempt, made through the same factory path the GUI and PGN code use. */
    static MoveTransition attempt(final Board board, final String from, final String to, final String promotion) {
        final Move move = promotion.isEmpty()
                ? MoveFactory.createMove(board, square(from), square(to))
                : MoveFactory.createPromotionMove(board, square(from), square(to), pieceType(promotion));
        return board.currentPlayer().makeMove(move);
    }

    private static Piece.PieceType pieceType(final String letter) {
        for (final Piece.PieceType type : Piece.PieceType.values()) {
            if (type.toString().equalsIgnoreCase(letter)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown piece " + letter);
    }

    /** Placement and side to move, the first two fields of a FEN. */
    static String placementAndTurn(final Board board) {
        final String[] parts = FenUtilities.createFENFromGame(board).split(" ");
        return parts[0] + " " + parts[1];
    }

    /** Every move the engine would truly accept in this position, in from-to notation. */
    static TreeSet<String> legalMoves(final Board board) {
        final TreeSet<String> moves = new TreeSet<>();
        for (final Move move : board.currentPlayer().getLegalMoves()) {
            final MoveTransition transition = board.currentPlayer().makeMove(move);
            if (transition.getMoveStatus().isDone()) {
                String uci = BoardUtils.INSTANCE.getPositionAtCoordinate(move.getCurrentCoordinate())
                        + BoardUtils.INSTANCE.getPositionAtCoordinate(move.getDestinationCoordinate());
                if (move instanceof Move.PawnPromotion) {
                    uci += transition.getToBoard().getPiece(move.getDestinationCoordinate())
                            .getPieceType().toString().toLowerCase();
                }
                moves.add(uci);
            }
        }
        return moves;
    }

    static TreeSet<String> parseMoves(final String text) {
        final TreeSet<String> moves = new TreeSet<>();
        for (final String uci : text.trim().split(" ")) {
            if (!uci.isEmpty()) {
                moves.add(uci);
            }
        }
        return moves;
    }

    static List<Map<String, String>> readCsv(final String fileName) {
        try {
            final List<String> lines = Files.readAllLines(DATA_DIR.resolve(fileName), StandardCharsets.UTF_8);
            final List<String> header = splitLine(lines.get(0));
            final List<Map<String, String>> rows = new ArrayList<>();
            for (final String line : lines.subList(1, lines.size())) {
                final List<String> cells = splitLine(line);
                final Map<String, String> row = new LinkedHashMap<>();
                for (int i = 0; i < header.size(); i++) {
                    row.put(header.get(i), cells.get(i));
                }
                rows.add(row);
            }
            return rows;
        } catch (final IOException e) {
            throw new IllegalStateException("Run from the BlackWidow-Chess folder: cannot read " + fileName, e);
        }
    }

    private static List<String> splitLine(final String line) {
        final List<String> cells = new ArrayList<>();
        final StringBuilder cell = new StringBuilder();
        boolean quoted = false;
        for (final char c : line.toCharArray()) {
            if (c == '"') {
                quoted = !quoted;
            } else if (c == ',' && !quoted) {
                cells.add(cell.toString());
                cell.setLength(0);
            } else {
                cell.append(c);
            }
        }
        cells.add(cell.toString());
        return cells;
    }
}
