"use client";
/**
 * MathText — renders a string that may contain inline LaTeX ($...$) or
 * display LaTeX ($$...$$) alongside plain text.
 *
 * Also handles bare LaTeX (no $ delimiters) returned by Gemini, e.g.
 * `P(A) = \frac{n(A)}{n(S)}` is auto-detected and rendered as math.
 */
import { InlineMath, BlockMath } from "react-katex";
import "katex/dist/katex.min.css";

interface Props {
  text: string;
  className?: string;
}

// Matches common LaTeX math commands that indicate a segment should be rendered as math
const LATEX_CMD_RE =
  /\\(?:frac|dfrac|sqrt|int|oint|iint|sum|prod|lim|log|ln|sin|cos|tan|cot|sec|csc|infty|alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Xi|Pi|Sigma|Upsilon|Phi|Psi|Omega|nabla|partial|forall|exists|cdot|times|div|pm|mp|leq|geq|neq|approx|equiv|rightarrow|leftarrow|Rightarrow|Leftarrow|to|implies|iff|ldots|cdots|binom|dbinom|overline|underline|hat|vec|bar|tilde|widehat|mathbb|mathbf|mathrm|text|left|right|begin|end)\b/;

// Matches bare ^nCr / ^nPr notation outside $ delimiters, e.g. ^8C_2 or ^{10}P_3
const NCR_RE = /\^\{?\d+\}?[CP]_?\{?\d+\}?/g;

/**
 * Pre-process: if text has NO $ delimiters but DOES contain LaTeX commands
 * or nCr/nPr notation, treat the whole string as a display-math block.
 */
function preProcess(text: string): string {
  const t = String(text ?? "");
  if (!t.includes("$") && (LATEX_CMD_RE.test(t) || NCR_RE.test(t))) {
    NCR_RE.lastIndex = 0; // reset after test
    return `$$${t}$$`;
  }
  return t;
}

/**
 * Second-pass: split a plain-text token that contains bare LaTeX commands
 * into sub-tokens of [plain-text, inline-math, plain-text, ...].
 * Handles cases like: "The area is \frac{1}{2}bh square units."
 */
function splitBareLatex(
  text: string,
): Array<{ type: "text" | "inline"; value: string }> {
  // Match bare LaTeX commands OR bare ^nCr / ^nPr notation
  const mathRe =
    /([A-Za-z0-9()=+\-*/^_.,'|\\]*\\[A-Za-z]+(?:\{(?:[^{}]|\{[^{}]*\})*\})*[A-Za-z0-9()=+\-*/^_.,'|]*|\^\{?\d+\}?[CP]_?\{?\d+\}?)/g;
  const out: Array<{ type: "text" | "inline"; value: string }> = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = mathRe.exec(text)) !== null) {
    if (m.index > last) {
      out.push({ type: "text", value: text.slice(last, m.index) });
    }
    out.push({ type: "inline", value: m[1] });
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    out.push({ type: "text", value: text.slice(last) });
  }
  return out.length > 1 ? out : [{ type: "text", value: text }]; // no split found
}

/** Returns true if the string contains bare LaTeX or bare nCr/nPr notation */
function hasBaremath(s: string): boolean {
  NCR_RE.lastIndex = 0;
  return LATEX_CMD_RE.test(s) || NCR_RE.test(s);
}

/** Split text into alternating plain-text and math tokens. */
function tokenise(raw: string): Array<{ type: "text" | "block" | "inline"; value: string }> {
  const text = preProcess(raw);
  const tokens: Array<{ type: "text" | "block" | "inline"; value: string }> = [];
  // Match $$...$$ first (block), then $...$ (inline)
  const re = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      const plain = text.slice(last, m.index);
      // Second pass: detect bare LaTeX or ^nCr/^nPr inside non-delimited text
      if (hasBaremath(plain)) {
        tokens.push(...splitBareLatex(plain));
      } else {
        tokens.push({ type: "text", value: plain });
      }
    }
    const chunk = m[0];
    if (chunk.startsWith("$$")) {
      tokens.push({ type: "block", value: chunk.slice(2, -2) });
    } else {
      tokens.push({ type: "inline", value: chunk.slice(1, -1) });
    }
    last = m.index + chunk.length;
  }
  if (last < text.length) {
    const tail = text.slice(last);
    if (hasBaremath(tail)) {
      tokens.push(...splitBareLatex(tail));
    } else {
      tokens.push({ type: "text", value: tail });
    }
  }
  return tokens;
}

export default function MathText({ text, className }: Props) {
  const tokens = tokenise(String(text ?? ""));
  return (
    <span className={className}>
      {tokens.map((tok, i) => {
        if (tok.type === "block") {
          return (
            <span key={i} className="block my-1 overflow-x-auto">
              <BlockMath math={tok.value} />
            </span>
          );
        }
        if (tok.type === "inline") {
          // Upgrade \binom to \dbinom so it renders full-size in inline mode
          const math = tok.value.replace(/\\binom\b/g, "\\dbinom");
          return (
            <span key={i}>
              <InlineMath math={math} />
            </span>
          );
        }
        return <span key={i}>{tok.value}</span>;
      })}
    </span>
  );
}
