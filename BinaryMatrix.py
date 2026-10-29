"""Gaussian elimination over GF(2), not real-valued matrix rank."""

import numpy as np

from Validation import positive_int


class BinaryMatrix:
    def __init__(self, matrix, rows, cols):
        positive_int(rows, "rows")
        positive_int(cols, "cols")
        rows, cols = int(rows), int(cols)
        array = np.asarray(matrix)
        if array.shape != (rows, cols):
            raise ValueError("Matrix shape must match the specified rows and columns.")
        if not np.all((array == 0) | (array == 1)):
            raise ValueError("A binary matrix may contain only 0 and 1.")
        self.M = rows
        self.Q = cols
        self.m = min(rows, cols)
        # The caller's array must not be changed by elimination.
        self.A = np.array(array, dtype=np.uint8, copy=True)

    def compute_rank(self, verbose=False):
        """Reduce to row echelon form and return the GF(2) rank.

        The pivot row advances only when a pivot is found; columns without pivots
        are skipped. This also handles rectangular and singular matrices.
        """
        pivot_row = 0
        for column in range(self.Q):
            candidates = np.flatnonzero(self.A[pivot_row:, column])
            if candidates.size == 0:
                continue
            self.swap_rows(pivot_row, pivot_row + int(candidates[0]))
            for row in range(pivot_row + 1, self.M):
                if self.A[row, column]:
                    self.A[row] ^= self.A[pivot_row]
            pivot_row += 1
            if pivot_row == self.M:
                break
        if verbose:
            print("GF(2) row echelon form:\n", self.A)
            print("Rank:", pivot_row)
        return pivot_row

    def perform_row_operations(self, i, forward_elimination):
        """Legacy helper: eliminate column i using the pivot at (i, i)."""
        rows = range(i + 1, self.M) if forward_elimination else range(i - 1, -1, -1)
        for row in rows:
            if self.A[row, i]:
                self.A[row] ^= self.A[i]

    def find_unit_element_swap(self, i, forward_elimination):
        """Legacy helper: find a unit entry in column i and swap its row."""
        rows = range(i + 1, self.M) if forward_elimination else range(i - 1, -1, -1)
        for row in rows:
            if self.A[row, i]:
                return self.swap_rows(i, row)
        return 0

    def swap_rows(self, i, ix):
        self.A[[i, ix]] = self.A[[ix, i]]
        return 1

    def determine_rank(self):
        """Return the GF(2) rank even when the matrix is not yet reduced."""
        return self.compute_rank()
