import ply.lex as lex
import ply.yacc as yacc
import string

[EMPTY, CHAR, DOT, STAR, BAR, CONCAT, GROUP, BACKREF] = range(8)
CHARSET = string.lowercase + string.uppercase + string.digits + " :/\'"

class RegexLexer:
    tokens = (
        "CHAR", "DOT",
        "STAR", "BAR",
        "LPAREN", "RPAREN",
        "LBRACKET", "RBRACKET", "DASH", "CARET",
        "PLUS", "QUESTION", "BACKSLASH", "DIGIT",
        "LBRACE", "RBRACE", "COMMA",
    )
    def t_CHAR(self, t):
        r"[a-zA-Z\s:/']"
        return t;
    def t_DIGIT(self, t):
        r"[0-9]"
        return t;
    t_DOT = r"\."
    t_STAR = r"\*"
    t_BAR = r"\|"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"
    t_DASH = r"\-"
    t_CARET = r"\^"
    t_PLUS = r"\+"
    t_QUESTION = r"\?"
    t_BACKSLASH = r"\\"
    t_LBRACE = r"\{"
    t_RBRACE = r"\}"
    t_COMMA = ","
    def t_error(self, t):
        print "Error parsing '%s'" % t.value[0]
    def __init__(self):
        self.lexer = lex.lex(module=self)

class RegexParser:
    precedence = (
        ('left', 'BAR'),
        ('left', 'DIGIT', 'DOT', 'CHAR'),
        ('left', 'CONCAT'),
        ('right', 'STAR', 'PLUS', 'QUESTION', 'LBRACE', 'RBRACE'),
        ('left', 'LBRACKET', 'LPAREN'),
        ('left', 'BACKSLASH'),
    )

    def p_regex_expr(self, p):
        """regex : expr"""
        p[0] = p[1]

    def p_expr_concat(self, p):
        """expr : expr expr %prec CONCAT"""
        p[0] = (CONCAT, p[1], p[2])

    def p_expr_group(self, p):
        """expr : LPAREN expr RPAREN"""
        self.groups.append(p[2])
        p[0] = (GROUP, len(self.groups), p[2])

    def p_expr_star(self, p):
        """expr : expr STAR"""
        p[0] = (STAR, p[1])

    def p_expr_plus(self, p):
        """expr : expr PLUS"""
        p[0] = (CONCAT, p[1], (STAR, p[1]))

    def p_expr_question(self, p):
        """expr : expr QUESTION"""
        p[0] = (BAR, p[1], (EMPTY,))

    def p_expr_dot(self, p):
        """expr : DOT"""
        p[0] = (DOT,)

    def p_expr_char(self, p):
        """
        expr : CHAR
             | DIGIT
             | DASH
             | COMMA
        """
        p[0] = (CHAR, p[1])

    def p_expr_backslash(self, p):
        """
        expr : BACKSLASH DIGIT
        """
        p[0] = (BACKREF, int(p[2]))
        self.backrefs.add(int(p[2]))

    def p_expr_escape(self, p):
        """
        expr : BACKSLASH DOT
             | BACKSLASH STAR
             | BACKSLASH PLUS
             | BACKSLASH QUESTION
             | BACKSLASH CARET
             | BACKSLASH BACKSLASH
             | BACKSLASH LPAREN
             | BACKSLASH RPAREN
             | BACKSLASH LBRACKET
             | BACKSLASH RBRACKET
             | BACKSLASH LBRACE
             | BACKSLASH RBRACE
             | BACKSLASH BAR
        """
        p[0] = (CHAR, p[2])

    def p_expr_bar(self, p):
        """expr : expr BAR expr"""
        p[0] = (BAR, p[1], p[3])

    def p_expr_bracket(self, p):
        """expr : LBRACKET inbracket RBRACKET"""
        s = p[2]
        s = map(lambda x: (CHAR, x), list(s))
        p[0] = reduce(lambda x, y: (BAR, x, y), s)

    def p_inbracket_nocaret(self, p):
        """inbracket : inbracket_nocaret"""
        p[0] = p[1]

    def p_inbracket_caret(self, p):
        """inbracket : CARET inbracket_nocaret"""
        p[0] = set(set(CHARSET) - p[2])

    def p_nocaret_char(self, p):
        """
        inbracket_nocaret : CHAR inbracket_nocaret
                          | DIGIT inbracket_nocaret
        """
        p[2].add(p[1])
        p[0] = p[2]

    def p_nocaret_range(self, p):
        """
        inbracket_nocaret : CHAR DASH CHAR inbracket_nocaret
                          | DIGIT DASH DIGIT inbracket_nocaret
        """
        begin = ord(p[1])
        end = ord(p[3])
        s = set(map(chr, range(begin, end+1)))
        p[0] = p[4].union(s)

    def p_nocaret_empty(self, p):
        """inbracket_nocaret : """
        p[0] = set()

    def p_expr_brace1(self, p):
        """expr : expr LBRACE number RBRACE"""
        inner = p[1]
        times = int(p[3])
        p[0] = reduce(lambda x, y: (CONCAT, x, y), [inner for _ in range(times)])

    def p_expr_brace2(self, p):
        """expr : expr LBRACE number COMMA RBRACE"""
        inner = p[1]
        times = int(p[3])
        before = reduce(lambda x, y: (CONCAT, x, y), [inner for _ in range(times)])
        p[0] = (CONCAT, before, (STAR, inner))

    def p_expr_brace3(self, p):
        """expr : expr LBRACE number COMMA number RBRACE"""
        inner = p[1]
        times1 = int(p[3])
        times2 = int(p[5])
        cases = []
        for l in range(times1, times2+1):
            case = reduce(lambda x, y: (CONCAT, x, y), [inner for _ in range(l)])
            cases.append(case)
        p[0] = reduce(lambda x, y: (BAR, x, y), cases)

    def p_number_digit(self, p):
        """number : DIGIT number"""
        p[0] = p[1] + p[2]

    def p_number_empty(self, p):
        """number : """
        p[0] = ""

    def p_error(self, p):
        print "Parse error at '%s'" % p.value
    def __init__(self):
        self.lexer = RegexLexer()
        self.tokens = self.lexer.tokens
        self.parser = yacc.yacc(module=self)
    def parse(self, data):
        data = data.replace("\\s"," ").replace("\\d","(0|1|2|3|4|5|6|7|8|9)")
        data = data.replace("\\w","[A-Z]")
        data = data.replace("\1","\\1").replace("\2","\\2").replace("\3","\\3")
        data = data.replace("\4","\\4").replace("\5","\\5").replace("\6","\\6")
        data = data.replace("\7","\\7").replace("\8","\\8").replace("\9","\\9")
        self.groups = []
        self.backrefs = set()
        root = self.parser.parse(data, self.lexer.lexer)
        return {'groups': self.groups, 'root': root, 'backrefs': self.backrefs}
