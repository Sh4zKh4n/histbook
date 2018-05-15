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

import numbers

import histbook.expr
import histbook.stmt

import numpy

class Axis(object):
    @staticmethod
    def _int(x, n):
        if not isinstance(x, (numbers.Integral, numpy.integer)):
            raise TypeError("{0} must be an integer".format(n))
        else:
            return int(x)

    @staticmethod
    def _nonnegint(x, n):
        if not isinstance(x, (numbers.Integral, numpy.integer)) or x < 0:
            raise TypeError("{0} must be a non-negative integer".format(n))
        else:
            return int(x)

    @staticmethod
    def _real(x, n):
        if not isinstance(x, (numbers.Real, numpy.floating)):
            raise TypeError("{0} must be a real number".format(n))
        else:
            return float(x)

    @staticmethod
    def _bool(x, n):
        if not isinstance(x, (bool, numpy.bool, numpy.bool_)):
            raise TypeError("{0} must be boolean".format(n))
        else:
            return bool(x)

    def __ne__(self, other):
        return not self.__eq__(other)

class GroupAxis(Axis): pass
class FixedAxis(Axis): pass
class ProfileAxis(Axis): pass

class groupby(GroupAxis):
    def __init__(self, expr):
        self._expr = expr

    def __repr__(self):
        return "groupby({0})".format(repr(self._expr))

    @property
    def expr(self):
        return self._expr

    def relabel(self, label):
        return groupby(label)

    def _goals(self, parsed=None):
        if parsed is None:
            parsed = histbook.expr.Expr.parse(self._expr)
        return [histbook.stmt.CallGraphGoal(histbook.expr.Call("histbook.groupby", parsed))]

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._expr == other._expr

    def __hash__(self):
        return hash((self.__class__, self._expr))

    def _only(self, cmp, value, content, tolerance):
        if cmp == "==":
            return self, lambda x: x == value, None, False
        elif cmp == "!=":
            return self, lambda x: x != value, None, False
        elif cmp == "<":
            return self, lambda x: x < value, None, False
        elif cmp == "<=":
            return self, lambda x: x <= value, None, False
        elif cmp == ">":
            return self, lambda x: x > value, None, False
        elif cmp == ">=":
            return self, lambda x: x >= value, None, False
        elif cmp == "in":
            return self, lambda x: x in value, None, False
        elif cmp == "not in":
            return self, lambda x: x not in value, None, False
        else:
            raise AssertionError(cmp)

class groupbin(GroupAxis):
    def __init__(self, expr, binwidth, origin=0, nanflow=True, closedlow=True):
        self._expr = expr
        self._binwidth = self._real(binwidth, "binwidth")
        self._origin = self._real(origin, "origin")
        self._nanflow = self._bool(nanflow, "nanflow")
        self._closedlow = self._bool(closedlow, "closedlow")

    def __repr__(self):
        args = [repr(self._expr), repr(self._binwidth)]
        if self._origin != 0:
            args.append("origin={0}".format(repr(self._origin)))
        if self._nanflow is not True:
            args.append("nanflow={0}".format(repr(self._nanflow)))
        if self._closedlow is not True:
            args.append("closedlow={0}".format(repr(self._closedlow)))
        return "groupbin({0})".format(", ".join(args))

    @property
    def expr(self):
        return self._expr

    @property
    def binwidth(self):
        return self._binwidth

    @property
    def origin(self):
        return self._origin

    @property
    def nanflow(self):
        return self._nanflow

    @property
    def closedlow(self):
        return self._closedlow

    def relabel(self, label):
        return groupbin(label, self._binwidth, origin=self._origin, nanflow=self._nanflow, closedlow=self._closedlow)

    def _goals(self, parsed=None):
        if parsed is None:
            parsed = histbook.expr.Expr.parse(self._expr)
        return [histbook.stmt.CallGraphGoal(histbook.expr.Call("histbook.groupbin{0}".format("L" if self._closedlow else "H"), parsed, histbook.expr.Const(self._binwidth), histbook.expr.Const(self._origin)))]

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._expr == other._expr and self._binwidth == other._binwidth and self._origin == other._origin and self._nanflow == other._nanflow and self._closedlow == other._closedlow

    def __hash__(self):
        return hash((self.__class__, self._expr, self._binwidth, self._origin, self._nanflow, self._closedlow))

    def _only(self, cmp, value, content, tolerance):
        if isinstance(value, (numbers.Real, numpy.floating, numpy.integer)):
            close = round((value - float(self._origin)) / float(self._binwidth)) * float(self._binwidth) + float(self._origin)
            if abs(value - close) < tolerance:
                if self._closedlow and cmp == "<":
                    return self, lambda x: x < close, close, False
                elif self._closedlow and cmp == ">=":
                    return self, lambda x: x >= close, close, False
                elif not self._closedlow and cmp == ">":
                    return self, lambda x: x >= close, close, False
                elif not self._closedlow and cmp == "<=":
                    return self, lambda x: x < close, close, False
                else:
                    return None, None, close, True
            else:
                return None, None, close, False
        else:
            return None, None, None, False

class bin(FixedAxis):
    def __init__(self, expr, numbins, low, high, underflow=True, overflow=True, nanflow=True, closedlow=True):
        self._expr = expr
        self._numbins = self._nonnegint(numbins, "numbins")
        self._low = self._real(low, "low")
        self._high = self._real(high, "high")
        if (self._numbins > 0 and self._low >= self._high) or (self._low > self._high):
            raise ValueError("low must not be greater than than high")
        self._underflow = self._bool(underflow, "underflow")
        self._overflow = self._bool(overflow, "overflow")
        self._nanflow = self._bool(nanflow, "nanflow")
        self._closedlow = self._bool(closedlow, "closedlow")
        self._checktot()

    def _checktot(self):
        if self.totbins == 0:
            raise ValueError("at least one bin is required (may be over/under/nanflow)")
        
    def __repr__(self):
        args = [repr(self._expr), repr(self._numbins), repr(self._low), repr(self._high)]
        if self._underflow is not True:
            args.append("underflow={0}".format(repr(self._underflow)))
        if self._overflow is not True:
            args.append("overflow={0}".format(repr(self._overflow)))
        if self._nanflow is not True:
            args.append("nanflow={0}".format(repr(self._nanflow)))
        if self._closedlow is not True:
            args.append("closedlow={0}".format(repr(self._closedlow)))
        return "bin({0})".format(", ".join(args))

    @property
    def expr(self):
        return self._expr

    @property
    def numbins(self):
        return self._numbins

    @property
    def low(self):
        return self._low

    @property
    def high(self):
        return self._high

    @property
    def underflow(self):
        return self._underflow

    @property
    def overflow(self):
        return self._overflow

    @property
    def nanflow(self):
        return self._nanflow

    @property
    def closedlow(self):
        return self._closedlow

    def relabel(self, label):
        return bin(label, self._numbins, self._low, self._high, underflow=self._underflow, overflow=self._overflow, nanflow=self._nanflow, closedlow=self._closedlow)

    @property
    def totbins(self):
        return self._numbins + (1 if self._underflow else 0) + (1 if self._overflow else 0) + (1 if self._nanflow else 0)

    def _goals(self, parsed=None):
        if parsed is None:
            parsed = histbook.expr.Expr.parse(self._expr)
        return [histbook.stmt.CallGraphGoal(histbook.expr.Call("histbook.bin{0}{1}{2}{3}".format("U" if self._underflow else "_", "O" if self._overflow else "_", "N" if self._nanflow else "_", "L" if self._closedlow else "H"), parsed, histbook.expr.Const(self._numbins), histbook.expr.Const(self._low), histbook.expr.Const(self._high)))]

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._expr == other._expr and self._numbins == other._numbins and self._low == other._low and self._high == other._high and self._underflow == other._underflow and self._overflow == other._overflow and self._nanflow == other._nanflow and self._closedlow == other._closedlow

    def __hash__(self):
        return hash((self.__class__, self._expr, self._numbins, self._low, self._high, self._underflow, self._overflow, self._nanflow, self._closedlow))

    def _only(self, cmp, value, content, tolerance):
        if isinstance(value, (numbers.Real, numpy.floating, numpy.integer)):
            scale = float(self._numbins) / float(self._high - self._low)
            edgenum = int(round((value - float(self._low)) * scale))
            close = min(self._numbins, max(0, edgenum)) / scale + float(self._low)

            if abs(value - close) < tolerance:
                out = self.__class__.__new__(self.__class__)
                out.__dict__.update(self.__dict__)

                if self._closedlow and cmp == "<":
                    out._numbins = edgenum
                    out._high = close
                    out._overflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(0, edgenum + (1 if self._underflow else 0)), close, False

                elif self._closedlow and cmp == ">=":
                    out._numbins = self._numbins - edgenum
                    out._low = close
                    out._underflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(edgenum + (1 if self._underflow else 0), self._numbins + (1 if self._underflow else 0) + (1 if out._overflow else 0)), close, False

                elif not self._closedlow and cmp == ">":
                    out._numbins = self._numbins - edgenum
                    out._low = close
                    out._underflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(edgenum + (1 if self._underflow else 0), self._numbins + (1 if self._underflow else 0) + (1 if out._overflow else 0)), close, False

                elif not self._closedlow and cmp == "<=":
                    out._numbins = edgenum
                    out._high = close
                    out._overflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(0, edgenum + (1 if self._underflow else 0)), close, False

                else:
                    return None, None, close, True
            else:
                return None, None, close, False
        else:
            return None, None, None, False
            
class intbin(FixedAxis):
    def __init__(self, expr, min, max, underflow=True, overflow=True):
        self._expr = expr
        self._min = self._int(min, "min")
        self._max = self._int(max, "max")
        self._underflow = self._bool(underflow, "underflow")
        self._overflow = self._bool(overflow, "overflow")
        self._checktot()

    def _checktot(self):
        if self._min > self._max:
            raise ValueError("min must not be greater than max")

    def __repr__(self):
        args = [repr(self._expr), repr(self._min), repr(self._max)]
        if self._underflow is not True:
            args.append("underflow={0}".format(repr(self._underflow)))
        if self._overflow is not True:
            args.append("overflow={0}".format(repr(self._overflow)))
        return "intbin({0})".format(", ".join(args))

    @property
    def expr(self):
        return self._expr

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def underflow(self):
        return self._underflow

    @property
    def overflow(self):
        return self._overflow

    def relabel(self, label):
        return intbin(label, self._min, self._max, underflow=self._underflow, overflow=self._overflow)

    @property
    def numbins(self):
        return self._max - self._min + 1

    @property
    def totbins(self):
        return self.numbins + (1 if self._underflow else 0) + (1 if self._overflow else 0)

    def _goals(self, parsed=None):
        if parsed is None:
            parsed = histbook.expr.Expr.parse(self._expr)
        return [histbook.stmt.CallGraphGoal(histbook.expr.Call("histbook.intbin{0}{1}".format("U" if self._underflow else "_", "O" if self._overflow else "_"), parsed, histbook.expr.Const(self._min), histbook.expr.Const(self._max)))]

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._expr == other._expr and self._min == other._min and self._max == other._max and self._underflow == other._underflow and self._overflow == other._overflow

    def __hash__(self):
        return hash((self.__class__, self._expr, self._min, self._max, self._underflow, self._overflow))

    def _only(self, cmp, value, content, tolerance):
        if isinstance(value, (numbers.Real, numpy.floating, numpy.integer)):
            if value + tolerance < self._min:
                return None, None, self._min, False
            if value - tolerance > self._max:
                return None, None, self._max, False

            if abs(value - round(value)) < tolerance:
                out = self.__class__.__new__(self.__class__)
                out.__dict__.update(self.__dict__)

                if cmp == "<":
                    out._max = int(round(value)) - 1
                    out._overflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(None, out._max - self._min + (1 if self._underflow else 0) + 1), round(value), False

                elif cmp == "<=":
                    out._max = int(round(value))
                    out._overflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(None, out._max - self._min + (1 if self._underflow else 0) + 1), round(value), False

                elif cmp == ">":
                    out._min = int(round(value)) + 1
                    out._underflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(out._min - self._min + (1 if self._underflow else 0), None), round(value), False

                elif cmp == ">=":
                    out._min = int(round(value))
                    out._underflow = False
                    out._nanflow = False
                    out._checktot()
                    return out, slice(out._min - self._min + (1 if self._underflow else 0), None), round(value), False

                else:
                    return None, None, round(value), True
            else:
                return None, None, round(value), False
        else:
            return None, None, None, False

class split(FixedAxis):
    def __init__(self, expr, edges, underflow=True, overflow=True, nanflow=True, closedlow=True):
        self._expr = expr
        if isinstance(edges, (numbers.Real, numpy.floating)):
            self._edges = (float(edges),)
        else:
            if len(edges) < 1 or not all(isinstance(x, (numbers.Real, numpy.floating)) for x in edges):
                raise TypeError("edges must be a non-empty list of real numbers")
            self._edges = tuple(sorted(float(x) for x in edges),)
        if len(self._edges) != len(set(self._edges)):
            raise ValueError("edges must all be distinct")
        self._underflow = self._bool(underflow, "underflow")
        self._overflow = self._bool(overflow, "overflow")
        self._nanflow = self._bool(nanflow, "nanflow")
        self._closedlow = self._bool(closedlow, "closedlow")

    def __repr__(self):
        args = [repr(self._expr), repr(self._edges)]
        if self._underflow is not True:
            args.append("underflow={0}".format(repr(self._underflow)))
        if self._overflow is not True:
            args.append("overflow={0}".format(repr(self._overflow)))
        if self._nanflow is not True:
            args.append("nanflow={0}".format(repr(self._nanflow)))
        if self._closedlow is not True:
            args.append("closedlow={0}".format(repr(self._closedlow)))
        return "split({0})".format(", ".join(args))

    @property
    def expr(self):
        return self._expr

    @property
    def edges(self):
        return self._edges

    @property
    def underflow(self):
        return self._underflow

    @property
    def overflow(self):
        return self._overflow

    @property
    def nanflow(self):
        return self._nanflow

    @property
    def closedlow(self):
        return self._closedlo

    def relabel(self, label):
        return split(label, self._edges, underflow=self._underflow, overflow=self._overflow, nanflow=self._nanflow, closedlow=self._closedlow)

    @property
    def numbins(self):
        return len(self._edges) - 1

    @property
    def totbins(self):
        return self.numbins + (1 if self._underflow else 0) + (1 if self._overflow else 0) + (1 if self._nanflow else 0)

    def _goals(self, parsed=None):
        if parsed is None:
            parsed = histbook.expr.Expr.parse(self._expr)
        return [histbook.stmt.CallGraphGoal(histbook.expr.Call("histbook.split{0}{1}{2}{3}".format("U" if self._underflow else "_", "O" if self._overflow else "_", "N" if self._nanflow else "_", "L" if self._closedlow else "H"), parsed, histbook.expr.Const(self._edges)))]

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._expr == other._expr and self._edges == other._edges and self._underflow == other._underflow and self._overflow == other._overflow and self._nanflow == other._nanflow and self._closedlow == other._closedlow

    def __hash__(self):
        return hash((self.__class__, self._expr, self._edges, self._underflow, self._overflow, self._nanflow, self._closedlow))
            
    def _only(self, cmp, value, content, tolerance):
        if isinstance(value, (numbers.Real, numpy.floating, numpy.integer)):
            dist, edgex, edgei = sorted(((abs(value - x), x, i) for i, x in enumerate(self._edges)), reverse=True)[0]

            if dist < tolerance:
                out = self.__class__.__new__(self.__class__)
                out.__dict__.update(self.__dict__)

                if self.closedlow and cmp == "<":
                    out._edges = self._edges[:edgei + 1]
                    out._overflow = False
                    out._nanflow = False
                    return out, slice(0, edgei + (1 if self._underflow else 0) + 1), edgex, False

                elif self.closedlow and cmp == ">=":
                    out._edges = self._edges[edgei:]
                    out._underflow = False
                    out._nanflow = False
                    return out, slice(edgei + (1 if self._underflow else 0), len(self._edges) + (1 if self._underflow else 0) + (1 if self._overflow else 0)), edgex, False

                elif not self.closedlow and cmp == ">":
                    out._edges = self._edges[edgei:]
                    out._underflow = False
                    out._nanflow = False
                    return out, slice(edgei + (1 if self._underflow else 0), len(self._edges) + (1 if self._underflow else 0) + (1 if self._overflow else 0)), edgex, False

                elif not self.closedlow and cmp == "<=":
                    out._edges = self._edges[:edgei + 1]
                    out._overflow = False
                    out._nanflow = False
                    return out, slice(0, edgei + (1 if self._underflow else 0) + 1), edgex, False

                else:
                    return None, None, close, True
            else:
                return None, None, close, False
        else:
            return None, None, None, False

class cut(FixedAxis):
    def __init__(self, expr):
        self._expr = expr

    def __repr__(self):
        return "cut({0})".format(repr(self._expr))

    @property
    def expr(self):
        return self._expr

    def relabel(self, label):
        return cut(label)

    @property
    def numbins(self):
        return 2

    @property
    def totbins(self):
        return self.numbins

    def _goals(self, parsed=None):
        if parsed is None:
            parsed = histbook.expr.Expr.parse(self._expr)
        return [histbook.stmt.CallGraphGoal(histbook.expr.Call("histbook.cut", parsed))]

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._expr == other._expr

    def __hash__(self):
        return hash((self.__class__, self._expr))

class profile(ProfileAxis):
    def __init__(self, expr):
        self._expr = expr

    def __repr__(self):
        return "profile({0})".format(repr(self._expr))

    @property
    def expr(self):
        return self._expr

    def relabel(self, label):
        return profile(label)

    def _goals(self, parsed=None):
        if parsed is None:
            parsed = histbook.expr.Expr.parse(self._expr)
        return [histbook.stmt.CallGraphGoal(parsed),
                histbook.stmt.CallGraphGoal(histbook.expr.Call("numpy.multiply", parsed, parsed))]

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._expr == other._expr

    def __hash__(self):
        return hash((self.__class__, self._expr))
