import type { CSSProperties, ElementType, ReactNode } from "react";
import { useReveal } from "../lib/hooks";

export function Reveal({
  as: Tag = "div",
  delay = 0,
  className = "",
  children,
}: {
  as?: ElementType;
  delay?: number;
  className?: string;
  children: ReactNode;
}) {
  const ref = useReveal<HTMLElement>();
  return (
    <Tag ref={ref} className={className} style={{ "--delay": `${delay}ms` } as CSSProperties}>
      {children}
    </Tag>
  );
}
