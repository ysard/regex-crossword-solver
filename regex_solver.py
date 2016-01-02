import z3
import regex_parser

_parser = regex_parser.RegexParser()

class RegexSolver:
    scratch_var_cnt = 0

    def __init__(self, length, regex, x):
        self.length = length
        parse_result = _parser.parse(regex)
        self.regex = parse_result['root']
        self.groups = parse_result['groups']
        self.x = x
        self.p = []
        self.possible_pos = [set() for _ in range(len(self.groups))]
        for i in range(len(self.groups)):
            self.p.append(z3.Int("p_%d" % RegexSolver.scratch_var_cnt))
            RegexSolver.scratch_var_cnt += 1

    def _len_set(self, r):
        ty = r[0]

        if ty == regex_parser.EMPTY:
            return set([0])

        elif ty == regex_parser.CHAR:
            return set([1])

        elif ty == regex_parser.DOT:
            return set([1])

        elif ty == regex_parser.STAR:
            # LEN(r) = { k * l <= MAX : k = 0,1,2,... && l in len_set(r) }
            s = set()
            for l in self._len_set(r[1]):
                k = 0
                while k * l <= self.length:
                    s.add(k * l)
                    k += 1
            return s

        elif ty == regex_parser.BAR:
            # LEN(r1 | r2) = LEN(r1) union LEN(r2)
            l1 = self._len_set(r[1])
            l2 = self._len_set(r[2])
            return l1 | l2

        elif ty == regex_parser.CONCAT:
            # LEN(r1 r2) = { l1 + l2 <= MAX : l1 in LEN(r1) and l2 in LEN(r2) }
            s = set()
            l1 = self._len_set(r[1])
            l2 = self._len_set(r[2])
            for i in l1:
                for j in l2:
                    if i + j <= self.length:
                        s.add(i + j)
            return s

        elif ty == regex_parser.GROUP:
            return self._len_set(r[2])

        elif ty == regex_parser.BACKREF:
            idx = r[1] - 1
            return self._len_set(self.groups[idx])

        else:
            raise ValueError("Unknown regex_parser type '%s'" % repr(ty))

    def _sat_expr(self, x, r, i, l):
        if l not in self._len_set(r):
            return False
        if i + l > self.length:
            return False

        ty = r[0]

        if ty == regex_parser.EMPTY:
            return True

        elif ty == regex_parser.CHAR:
            return (x[i] == ord(r[1]))

        elif ty == regex_parser.DOT:
            expr = False
            for ch in regex_parser.CHARSET:
                expr = z3.Or(expr, x[i] == ord(ch))
            return expr

        elif ty == regex_parser.STAR:
            # SAT(r*, i, l) = Union for l' in LEN(r):
            #                   [ SAT(r, i, l') && SAT(r*, i+l', l-l') ]
            if l == 0:
                return True
            else:
                expr = False
                for l1 in self._len_set(r[1]):
                    expr = z3.Or(expr, z3.And(
                        self._sat_expr(x, r[1], i, l1),
                        self._sat_expr(x, r, i + l1, l - l1)
                    ))
                return expr

        elif ty == regex_parser.BAR:
            # SAT(r1 | r2, i, l) = SAT(r1, i, l) || SAT(r2, i, l)
            expr = z3.Or(
                    self._sat_expr(x, r[1], i, l),
                    self._sat_expr(x, r[2], i, l)
            )
            return expr

        elif ty == regex_parser.CONCAT:
            # SAT(r1 r2, i, l) = Union for l1 in LEN(r1):
            #                      [ SAT(r1, i, l1) && SAT(r2, i+l1, l-l1) ]
            expr = False
            for l1 in self._len_set(r[1]):
                expr = z3.Or(expr, z3.And(
                    self._sat_expr(x, r[1], i, l1),
                    self._sat_expr(x, r[2], i + l1, l - l1)
                ))
            return expr

        elif ty == regex_parser.GROUP:
            idx = r[1] - 1
            inner = r[2]
            expr = z3.And(
                    (self.p[idx] == i),
                    self._sat_expr(x, inner, i, l)
            )
            self.possible_pos[idx].add(i)
            return expr

        elif ty == regex_parser.BACKREF:
            idx = r[1] - 1
            expr = False
            for j in self.possible_pos[idx]:
                clause = (self.p[idx] == j)
                for k in range(l):
                    clause = z3.And(clause, (x[i+k] == x[j+k]))
                expr = z3.Or(expr, clause)
            return expr

        else:
            raise ValueError("Unknown regex_parser type '%s'" % repr(ty))

    def sat_expr(self):
        expr = self._sat_expr(self.x, self.regex, 0, self.length)
        return z3.simplify(expr)

