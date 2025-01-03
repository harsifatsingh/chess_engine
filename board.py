from move import Move
from pieces.pawn import Pawn
from pieces.rook import Rook
from pieces.knight import Knight
from pieces.bishop import Bishop
from pieces.queen import Queen
from pieces.king import King

class Board:
    def __init__(self):
        """
        Initialize an 8x8 board as a 2D list.
        None means no piece on that square.
        """
        self.squares = self._create_empty_board()

        self.white_can_castle_kingside = True
        self.white_can_castle_queenside = True
        self.black_can_castle_kingside = True
        self.black_can_castle_queenside = True

        # Track which square is available for en passant capture, e.g. (3,4)
        # or None if no en passant is possible
        self.en_passant_target = None

        # Move history for undo
        self.move_history = []

    def _create_empty_board(self):
        """
        Helper to create an 8x8 grid of None.
        """
        return [[None for _ in range(8)] for _ in range(8)]

    def setup_initial_position(self):
        """
        Place all pieces in their initial positions.
        """
        # Pawns
        for col in range(8):
            self.squares[1][col] = Pawn("WHITE")
            self.squares[6][col] = Pawn("BLACK")

        # Rooks
        self.squares[0][0] = Rook("WHITE")
        self.squares[0][7] = Rook("WHITE")
        self.squares[7][0] = Rook("BLACK")
        self.squares[7][7] = Rook("BLACK")

        # Knights
        self.squares[0][1] = Knight("WHITE")
        self.squares[0][6] = Knight("WHITE")
        self.squares[7][1] = Knight("BLACK")
        self.squares[7][6] = Knight("BLACK")

        # Bishops
        self.squares[0][2] = Bishop("WHITE")
        self.squares[0][5] = Bishop("WHITE")
        self.squares[7][2] = Bishop("BLACK")
        self.squares[7][5] = Bishop("BLACK")

        # Queens
        self.squares[0][3] = Queen("WHITE")
        self.squares[7][3] = Queen("BLACK")

        # Kings
        self.squares[0][4] = King("WHITE")
        self.squares[7][4] = King("BLACK")

    def parse_move_string(self, move_str, color):
        """
        Given a string like 'e2e4', convert to a Move object.
        If invalid format, return None.
        """
        if len(move_str) < 4:
            return None

        # Convert algebraic notation: 'a' -> col=0, 'b'->1... 'h'->7
        start_col = ord(move_str[0]) - ord('a')
        start_row = 8 - int(move_str[1])  # '1' -> row=7, '2'->6, etc.
        end_col = ord(move_str[2]) - ord('a')
        end_row = 8 - int(move_str[3])

        # Basic validation
        if not (0 <= start_row < 8 and 0 <= start_col < 8):
            return None
        if not (0 <= end_row < 8 and 0 <= end_col < 8):
            return None

        piece_moved = self.squares[start_row][start_col]
        if piece_moved is None or piece_moved.color != color:
            # No piece of the correct color at start square
            return None

        piece_captured = self.squares[end_row][end_col]
        return Move(start_row, start_col, end_row, end_col, piece_moved, piece_captured)

    def get_piece_at(self, row, col):
        return self.squares[row][col]

    def set_piece_at(self, row, col, piece):
        self.squares[row][col] = piece

    def is_legal_move(self, move, color):
        self.make_move(move)
        legal = not self.is_in_check(color)
        self.undo_move()
        return legal

    def make_move(self, move):
        """
        Update the board for the given move:
        - Move the piece on start -> end.
        - Replace (capture) or set None on start.
        """
        start_piece = move.piece_moved
        self.move_history.append((move, self.white_can_castle_kingside, self.white_can_castle_queenside,
                                  self.black_can_castle_kingside, self.black_can_castle_queenside,
                                  self.en_passant_target))
        
        self.squares[move.end_row][move.end_col] = start_piece
        self.squares[move.start_row][move.start_col] = None

        self.handle_special_moves(move)

    def handle_special_moves(self, move):
        piece = move.piece_moved
        start_row, start_col = move.start_row, move.start_col
        end_row, end_col = move.end_row, move.end_col

        self.en_passant_target = None

        # Pawn-specific logic
        if isinstance(piece, Pawn):
            # En passant capture
            # If we moved diagonally to an empty square that was the en_passant_target
            if (start_col != end_col and move.piece_captured is None):
                # So the captured pawn must be behind end_row
                captured_row = start_row  # The pawn is on the row we started from
                self.squares[captured_row][end_col] = None

            # If the pawn moved two squares, set en_passant_target
            if abs(end_row - start_row) == 2:
                # This is the row *between* start_row & end_row
                row_direction = 1 if piece.color == "BLACK" else -1
                self.en_passant_target = (end_row + row_direction, end_col)

            # Promotion
            if (end_row == 0 and piece.color == "WHITE") or (end_row == 7 and piece.color == "BLACK"):
                if move.promotion:
                    promo_char = move.promotion.upper()  # 'Q', 'R', 'N', 'B'
                    if promo_char == 'Q':
                        self.squares[end_row][end_col] = Queen(piece.color)
                    elif promo_char == 'R':
                        self.squares[end_row][end_col] = Rook(piece.color)
                    elif promo_char == 'N':
                        self.squares[end_row][end_col] = Knight(piece.color)
                    elif promo_char == 'B':
                        self.squares[end_row][end_col] = Bishop(piece.color)
                else:
                    # Default to queen if none specified
                    self.squares[end_row][end_col] = Queen(piece.color)

        # Castling            
        if isinstance(piece, King):
            # If king moves two squares horizontally, it's castling
            if abs(end_col - start_col) == 2:
                # King side or queen side?
                if end_col == 6:  # King-side (short) castling
                    # Move the rook from col 7 to col 5
                    rook = self.squares[end_row][7]
                    self.squares[end_row][5] = rook
                    self.squares[end_row][7] = None
                else:  # end_col == 2 => Queen-side
                    rook = self.squares[end_row][0]
                    self.squares[end_row][3] = rook
                    self.squares[end_row][0] = None

        # If we move a king or rook, update castling rights
        if isinstance(piece, King):
            if piece.color == "WHITE":
                self.white_can_castle_kingside = False
                self.white_can_castle_queenside = False
            else:
                self.black_can_castle_kingside = False
                self.black_can_castle_queenside = False

        if isinstance(piece, Rook):
            if piece.color == "WHITE":
                if start_row == 7 and start_col == 7:
                    self.white_can_castle_kingside = False
                if start_row == 7 and start_col == 0:
                    self.white_can_castle_queenside = False
            else:
                if start_row == 0 and start_col == 7:
                    self.black_can_castle_kingside = False
                if start_row == 0 and start_col == 0:
                    self.black_can_castle_queenside = False

    def undo_move(self):
        if not self.move_history:
            return
        (move,
         w_cks, w_cqs,
         b_cks, b_cqs,
         enp) = self.move_history.pop()
        self.white_can_castle_kingside = w_cks
        self.white_can_castle_queenside = w_cqs
        self.black_can_castle_kingside = b_cks
        self.black_can_castle_queenside = b_cqs
        self.en_passant_target = enp

        start_row, start_col = move.start_row, move.start_col
        end_row, end_col = move.end_row, move.end_col
        self.squares[start_row][start_col] = move.piece_moved
        self.squares[end_row][end_col] = move.piece_captured

        # Special handling for undoing castling
        if isinstance(move.piece_moved, King) and abs(end_col - start_col) == 2:
            # Moved two squares => castling
            if end_col == 6:
                # Rook from col 5 back to col 7
                rook = self.squares[end_row][5]
                self.squares[end_row][7] = rook
                self.squares[end_row][5] = None
            else:
                # Rook from col 3 back to col 0
                rook = self.squares[end_row][3]
                self.squares[end_row][0] = rook
                self.squares[end_row][3] = None

        # Special undo for en passant
        # If we captured a pawn en passant, the captured piece would be at move.start_row, end_col
        if isinstance(move.piece_moved, Pawn):
            if move.piece_captured is None and (move.start_col != move.end_col):
                # So we must restore the captured pawn
                row_direction = 1 if move.piece_moved.color == "WHITE" else -1
                self.squares[move.end_row][move.end_col] = None
                self.squares[move.start_row][move.end_col] = Pawn("WHITE" if move.piece_moved.color == "BLACK" else "BLACK")

        # Special undo for promotion
        if isinstance(move.piece_moved, Pawn):
            # If end square is a Queen/Bishop/Rook/Knight of same color, revert to a pawn
            piece_now = self.squares[start_row][start_col]
            if not isinstance(piece_now, Pawn):
                # Revert to a Pawn
                self.squares[start_row][start_col] = Pawn(piece_now.color)

    def generate_legal_moves(self, color):
        """
        Generate all pseudo-legal moves for the given color 
        (NOT checking for check or checkmate for this example).
        """
        moves = []
        for row in range(8):
            for col in range(8):
                piece = self.squares[row][col]
                if piece and piece.color == color:
                    piece_moves = piece.get_legal_moves(self, row, col)
                    moves.extend(piece_moves)

        # Filter out moves that leave own king in check
        legal_moves = []
        for move in moves:
            if self.is_legal_move(move, color):
                legal_moves.append(move)
        return legal_moves

    def is_in_check(self, color):
        king_pos = None
        for row in range(8):
            for col in range(8):
                piece = self.squares[row][col]
                if piece and piece.color == color and piece.symbol().upper() == 'K':
                    king_pos = (row, col)
                    break
            if king_pos:
                break

        if not king_pos:
            return False
        king_row, king_col = king_pos

        enemy_color = "WHITE" if color == "BLACK" else "BLACK"
        all_enemy_moves = self.generate_legal_moves(enemy_color)
        for m in all_enemy_moves:
            if m.end_row == king_row and m.end_col == king_col:
                return True
        return False
    
    def is_checkmate(self, color):
        """
        Check if the given color is in checkmate: 
        - King is in check
        - No legal moves
        """
        if not self.is_in_check(color):
            return False
        moves = self.generate_legal_moves(color)
        return len(moves) == 0

    def is_stalemate(self, color):
        if self.is_in_check(color):
            return False
        moves = self.generate_legal_moves(color)
        return len(moves) == 0

    def __str__(self):
        """
        Return a string representation of the board.
        Top row is row=0 in our matrix, but visually it's rank 8 in chess.
        """
        board_str = ""
        for row in range(8):
            rank_str = f"{8 - row} "
            for col in range(8):
                piece = self.squares[row][col]
                rank_str += f"{str(piece) if piece else '.'} "
            board_str += rank_str + "\n"
        board_str += "  a b c d e f g h\n"
        return board_str
