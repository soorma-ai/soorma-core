// SPDX-License-Identifier: Apache-2.0
//
// Checks that a schema `pattern` is portable and linear-time (NFR-WC-08; D-CG-05).
//
// Portable: anchored, and in the RE2-compatible subset: no lookaround, no
// backreference, no named group. Such a pattern matches in linear time in an
// RE2 engine. Ajv runs patterns in V8's backtracking engine, where linearity
// also needs unambiguous repetition, so one more rule applies: a group under an
// unbounded quantifier (`*`, `+`, `{n,}`) must start, in every alternative,
// with a literal character that nothing else in the group can match.
//
// The parser covers the syntax the contract uses: literals, escapes, character
// classes with ranges, groups with alternation, and quantifiers.

type Range = [number, number];

interface CharNode {
  kind: 'char';
  ranges: Range[];
  literal: boolean;
}
interface GroupNode {
  kind: 'group';
  alternatives: Seq[];
}
interface AnchorNode {
  kind: 'anchor';
}
type Atom = CharNode | GroupNode | AnchorNode;
interface Item {
  atom: Atom;
  unbounded: boolean;
}
type Seq = Item[];

export class PatternSyntaxError extends Error {}

const ESCAPE_CLASSES: Record<string, Range[]> = {
  d: [[0x30, 0x39]],
  w: [
    [0x30, 0x39],
    [0x41, 0x5a],
    [0x5f, 0x5f],
    [0x61, 0x7a],
  ],
  s: [
    [0x09, 0x0d],
    [0x20, 0x20],
  ],
};
const ESCAPE_CHARS: Record<string, number> = { t: 0x09, n: 0x0a, r: 0x0d, f: 0x0c, v: 0x0b };

class Parser {
  private i = 0;
  private readonly src: string;
  constructor(src: string) {
    this.src = src;
  }

  parse(): Seq[] {
    const alternatives = this.alternatives();
    if (this.i < this.src.length) throw new PatternSyntaxError(`unexpected ')' at ${this.i}`);
    return alternatives;
  }

  private peek(): string | undefined {
    return this.src[this.i];
  }

  private alternatives(): Seq[] {
    const alts: Seq[] = [this.sequence()];
    while (this.peek() === '|') {
      this.i++;
      alts.push(this.sequence());
    }
    return alts;
  }

  private sequence(): Seq {
    const seq: Seq = [];
    while (this.i < this.src.length && this.peek() !== '|' && this.peek() !== ')') {
      const atom = this.atom();
      seq.push({ atom, unbounded: this.quantifier() });
    }
    return seq;
  }

  private atom(): Atom {
    const c = this.src[this.i++] as string;
    if (c === '^' || c === '$') return { kind: 'anchor' };
    if (c === '(') {
      if (this.peek() === '?') {
        const rest = this.src.slice(this.i, this.i + 3);
        if (rest.startsWith('?:')) {
          this.i += 2;
        } else if (/^\?(=|!|<=|<!)/.test(rest)) {
          throw new PatternSyntaxError('lookaround is not allowed');
        } else if (rest.startsWith('?<')) {
          throw new PatternSyntaxError('named groups are not allowed');
        } else {
          throw new PatternSyntaxError(`unsupported group syntax at ${this.i}`);
        }
      }
      const alternatives = this.alternatives();
      if (this.src[this.i++] !== ')') throw new PatternSyntaxError('unclosed group');
      return { kind: 'group', alternatives };
    }
    if (c === '[') return this.charClass();
    if (c === '\\') return this.escape();
    if (c === '.') return { kind: 'char', ranges: [[0, 0x10ffff]], literal: false };
    if ('*+?{'.includes(c))
      throw new PatternSyntaxError(`quantifier without an atom at ${this.i - 1}`);
    const cp = c.codePointAt(0) as number;
    return { kind: 'char', ranges: [[cp, cp]], literal: true };
  }

  private escape(): CharNode {
    const c = this.src[this.i++];
    if (c === undefined) throw new PatternSyntaxError('dangling escape');
    if (/[1-9]/.test(c)) throw new PatternSyntaxError('backreferences are not allowed');
    if (c === 'k') throw new PatternSyntaxError('named backreferences are not allowed');
    const cls = ESCAPE_CLASSES[c.toLowerCase()];
    if (cls) {
      if (c !== c.toLowerCase())
        throw new PatternSyntaxError(`negated class \\${c} is not supported`);
      return { kind: 'char', ranges: cls, literal: false };
    }
    const cp = ESCAPE_CHARS[c] ?? c.codePointAt(0) ?? 0;
    return { kind: 'char', ranges: [[cp, cp]], literal: true };
  }

  private classChar(): number {
    const c = this.src[this.i++];
    if (c === undefined) throw new PatternSyntaxError('unclosed character class');
    if (c !== '\\') return c.codePointAt(0) as number;
    const e = this.src[this.i++];
    if (e === undefined) throw new PatternSyntaxError('dangling escape');
    if (ESCAPE_CLASSES[e.toLowerCase()]) {
      throw new PatternSyntaxError(`class escape \\${e} inside a character class is not supported`);
    }
    return ESCAPE_CHARS[e] ?? (e.codePointAt(0) as number);
  }

  private charClass(): CharNode {
    if (this.peek() === '^')
      throw new PatternSyntaxError('negated character classes are not supported');
    const ranges: Range[] = [];
    while (this.peek() !== ']') {
      if (this.i >= this.src.length) throw new PatternSyntaxError('unclosed character class');
      const lo = this.classChar();
      if (this.peek() === '-' && this.src[this.i + 1] !== ']') {
        this.i++;
        const hi = this.classChar();
        if (hi < lo) throw new PatternSyntaxError('character class range out of order');
        ranges.push([lo, hi]);
      } else {
        ranges.push([lo, lo]);
      }
    }
    this.i++;
    return { kind: 'char', ranges, literal: false };
  }

  private quantifier(): boolean {
    const c = this.peek();
    if (c === '*' || c === '+') {
      this.i++;
      this.lazy();
      return true;
    }
    if (c === '?') {
      this.i++;
      this.lazy();
      return false;
    }
    if (c === '{') {
      const m = /^\{(\d+)(,(\d*))?\}/.exec(this.src.slice(this.i));
      if (!m) throw new PatternSyntaxError(`malformed quantifier at ${this.i}`);
      this.i += m[0].length;
      this.lazy();
      return m[2] !== undefined && m[3] === '';
    }
    return false;
  }

  private lazy(): void {
    if (this.peek() === '?') throw new PatternSyntaxError('lazy quantifiers are not supported');
  }
}

function overlaps(a: Range[], b: Range[]): boolean {
  return a.some(([lo, hi]) => b.some(([lo2, hi2]) => lo <= hi2 && lo2 <= hi));
}

/** Every character node in a sequence, recursively. */
function charNodes(seq: Seq): CharNode[] {
  const out: CharNode[] = [];
  for (const { atom } of seq) {
    if (atom.kind === 'char') out.push(atom);
    else if (atom.kind === 'group')
      for (const alt of atom.alternatives) out.push(...charNodes(alt));
  }
  return out;
}

function checkUnboundedGroups(alts: Seq[], problems: string[]): void {
  for (const seq of alts) {
    for (const { atom, unbounded } of seq) {
      if (atom.kind !== 'group') continue;
      if (unbounded) {
        for (const alt of atom.alternatives) {
          const first = alt[0];
          if (!first || first.atom.kind !== 'char' || !first.atom.literal || first.unbounded) {
            problems.push(
              'a group under an unbounded quantifier must start with a literal character in every alternative',
            );
            continue;
          }
          const lead = first.atom.ranges;
          const rest = charNodes(alt.slice(1));
          const others = atom.alternatives.filter((a) => a !== alt).flatMap((a) => charNodes(a));
          if ([...rest, ...others].some((n) => overlaps(n.ranges, lead))) {
            problems.push(
              `a group under an unbounded quantifier starts with '${String.fromCodePoint(lead[0]![0])}', which the group's body can also match`,
            );
          }
        }
      }
      checkUnboundedGroups(atom.alternatives, problems);
    }
  }
}

/** Problems with a pattern; empty when it is portable and linear-time. */
export function patternProblems(pattern: string): string[] {
  const problems: string[] = [];
  if (!pattern.startsWith('^')) problems.push("not anchored: must start with '^'");
  if (!pattern.endsWith('$') || pattern.endsWith('\\$'))
    problems.push("not anchored: must end with '$'");
  try {
    new RegExp(pattern, 'u');
  } catch (error) {
    problems.push(`does not compile with the u flag: ${(error as Error).message}`);
    return problems;
  }
  try {
    const alts = new Parser(pattern).parse();
    checkUnboundedGroups(alts, problems);
  } catch (error) {
    if (error instanceof PatternSyntaxError) problems.push(error.message);
    else throw error;
  }
  return problems;
}
