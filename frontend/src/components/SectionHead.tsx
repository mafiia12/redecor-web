import { Reveal } from "./Reveal";

/** Shared section header: small index + label on top, title on one side, intro on the other (desktop). */
export function SectionHead({ id, index, eyebrow, title, sub, aside }: { id?: string; index?: string; eyebrow?: string; title: string; sub?: string; aside?: React.ReactNode }) {
  return (
    <Reveal className="sh">
      {(index || eyebrow) && (
        <span className="sh__eyebrow">
          {index && <b>{index}</b>}
          {eyebrow}
        </span>
      )}
      <div className="sh__row">
        <h2 className="sh__title" id={id}>{title}</h2>
        {(sub || aside) && (
          <div className="sh__aside">
            {sub && <p>{sub}</p>}
            {aside}
          </div>
        )}
      </div>
    </Reveal>
  );
}
