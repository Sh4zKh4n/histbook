#!/usr/bin/env python

# Copyright (c) 2017, DIANA-HEP
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import histbook.axis
import histbook.expr

class Projectable(object):
    def axis(self, expr):
        expr = histbook.expr.Expr.parse(expr, defs=self._defs)
        for axis in self._group + self._fixed + self._profile:
            if expr == axis._parsed:
                return axis
        raise ValueError("no such axis: {0}".format(repr(str(expr))))

    def only(self, expr, tolerance=1e-12):
        expr = histbook.expr.Expr.parse(expr, defs=self._defs)

        if isinstance(expr, histbook.expr.LogicalAnd):
            out = None
            for arg in expr.args:
                if out is None:
                    out = self._only(arg, tolerance)
                else:
                    out = out._only(arg, tolerance)
            return out

        else:
            return self._only(expr, tolerance)

    def _only(self, expr, tolerance):
        cutexpr = expr
        if not isinstance(expr, (histbook.expr.Relation, histbook.expr.Logical)):
            raise TypeError("selection expression must be boolean, not {0}".format(repr(str(expr))))

        if isinstance(cutexpr, histbook.expr.Relation):
            cutcmp = cutexpr.cmp
            if isinstance(cutexpr.left, histbook.expr.Const):
                cutvalue, cutexpr = cutexpr.left, cutexpr.right
                cutcmp = {"<": ">", "<=": ">="}.get(cutcmp, cutcmp)
            else:
                cutexpr, cutvalue = cutexpr.left, cutexpr.right

            if not isinstance(cutvalue, histbook.expr.Const):
                raise TypeError("selection expression must have a constant left or right hand side, not {0}".format(repr(str(expr))))
            if isinstance(cutexpr, histbook.expr.Const):
                raise TypeError("selection expression must have a variable left or right hand side, not {0}".format(repr(str(expr))))

            cutvalue = cutvalue.value   # unbox to Python

        else:
            cutcmp = "=="
            cutvalue = True

        out = self.__class__.__new__(self.__class__)
        out.__dict__.update(self.__dict__)

        closest, closestaxis, wrongcmpaxis = None, None, None
        allaxis = self._group + self._fixed
        for axis in allaxis:
            if cutexpr == axis._parsed:
                newaxis, cutslice, close, wrongcmp = axis._only(cutcmp, cutvalue, out._content, tolerance)
                if newaxis is not None:
                    cutaxis = axis
                    break
                if close is not None and (closest is None or abs(cutvalue - close) < abs(cutvalue - closest)):
                    closest = close
                    closestaxis = axis
                if wrongcmp:
                    wrongcmpaxis = axis

        else:
            if wrongcmpaxis is not None:
                raise ValueError("no axis can select {0} (axis {1} has the wrong inequality; low edges are {2})".format(repr(str(expr)), wrongcmpaxis, "closed" if wrongcmpaxis.closedlow else "open"))
            elif closestaxis is not None:
                raise ValueError("no axis can select {0} (axis {1} has an edge at {2})".format(repr(str(expr)), closestaxis, repr(closest)))
            else:
                raise ValueError("no axis can select {0}".format(repr(str(expr))))
            
        def cutcontent(i, content):
            if content is None:
                return None

            if isinstance(allaxis[i], (histbook.axis.groupby, histbook.axis.groupbin)):
                if allaxis[i] is cutaxis:
                    return dict((n, x) for n, x in content.items() if cutslice(n))
                else:
                    return dict((n, cutcontent(i + 1, x)) for n, x in content.items())

            else:
                return content[tuple(cutslice if j < len(allaxis) and allaxis[j] is cutaxis else slice(None) for j in range(i, len(allaxis) + 1))].copy()

        out._group = tuple(newaxis if x is cutaxis else x for x in self._group)
        out._fixed = tuple(newaxis if x is cutaxis else x for x in self._fixed)
        out._content = cutcontent(0, self._content)
        return out
