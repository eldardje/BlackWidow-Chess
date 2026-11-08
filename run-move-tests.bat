@echo off
rem Builds and runs the move-legality tests. Needs JDK 21 or newer. Run from the BlackWidow-Chess folder.
if exist out\movetests rmdir /s /q out\movetests
mkdir out\movetests
javac -nowarn -d out\movetests -cp "lib/*" -sourcepath src src\com\chess\engine\board\Board.java src\com\chess\pgn\FenUtilities.java test\com\chess\movetests\*.java
if errorlevel 1 exit /b 1
java -cp "out\movetests;lib/*" org.junit.runner.JUnitCore com.chess.movetests.MoveTestSuite
