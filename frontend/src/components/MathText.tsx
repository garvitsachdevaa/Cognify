"use client";
/**
 * MathText — renders a string that may contain inline LaTeX ($...$) or
 * display LaTeX ($$...$$) alongside plain text.
 */
import { InlineMath, BlockMath } from "react-katex";
import "katex/dist/katex.min.css";

interface Props {
  text: string;
  className?: string;
}

/** Split text into alternating plain-text and math tokens. */
function tokenise(text: string): Array<{ type: "text" | "block" | "inline"; value: string }> {
  const tokens: Array<{ type: "text" | "block" | "inline"; value: string }> = [];
  // Match $$...$$ first (block), then $...$ (inline)
  const re = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      tokens.push({ type: "text", value: text.slice(last, m.index) });
    }
    const raw = m[0];
    if (raw.startsWith("$$")) {
      tokens.push({ type: "block", value: raw.slice(2, -2) });
    } else {
      tokens.push({ type: "inline", value: raw.slice(1, -1) });
    }
    last = m.index + raw.length;
  }
  if (last < text.length) {
    tokens.push({ type: "text", value: text.slice(last) });
  }
  return tokens;
}

export default function MathText({ text, className }: Props) {
  const tokens = tokenise(text);
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
          return (
            <span key={i}>
              <InlineMath math={tok.value} />
            </span>
          );
        }
        return <span key={i}>{tok.value}</span>;
      })}
    </span>
  );
}
