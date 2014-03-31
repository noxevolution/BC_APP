#!/usr/bin/env python

####################################################################################
#
#       SparseMatrix(N): an NxN sparse matrix, derived from the builtin list class.
#
#       The rows of the matrix are stored in a list.
#       The column values in one row are stored in a dict.
#       A value is only stored in the matrix if it is non-zero.
#
####################################################################################

import sys


class SparseMatrix(list):
    def __init__(self,N):
        super(SparseMatrix,self).__init__([ dict() for i in range(N) ])
        self.N = N
    def issparse(self):                 # yup. always sparse.
        return True
    def issymmetrical(self):            # symmetry is not assumed, nor is it known for this SparseMatrix
        return False
    def get(self,i,j):
        return self[i][j] if j in self[i] else 0

    @staticmethod
    def tunit(verbose):
        n = 100
        mat = SparseMatrix(n)
        # checkerboard fill, i.e. only cells[i][j] where i+j is even
        s1 = 0
        u = 1
        for i in range(n):
            for j in range(n):
                if (i+j) % 2 == 0:
                    mat[i][j] = u
                    s1 += u
                    u += 1
        assert s1 == u*(u-1)/2
        s2 = 0
        for i in range(n):
            for j in mat[i]:
                s2 += mat[i][j]
        assert s2 == s1

        print "SparseMatrix okey dokey"


if __name__ == '__main__':
    SparseMatrix.tunit(len(sys.argv) > 1)

