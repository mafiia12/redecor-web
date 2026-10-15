import { useSearchParams } from "react-router-dom";
import { ProjectCard, ProjectGridSkeleton } from "../components/Cards";
import { Segmented } from "../components/Filters";
import { useData, useLang, usePageMeta } from "../lib/context";
import type { Country, ProjectType } from "../lib/api";

const TYPES: ProjectType[] = ["residential", "hospitality", "retail", "office", "industrial", "healthcare", "public", "education"];
const COUNTRIES: Country[] = ["eg", "qa", "sa"];

export default function Projects() {
  const { t } = useLang();
  const { data, error, reload } = useData();
  const [params, setParams] = useSearchParams();
  usePageMeta(`${t.projects.title} | ${t.brand}`, t.projects.description);

  // Filters live in the URL (?country=qa&type=office) so filtered views can be shared.
  const rawCountry = params.get("country");
  const rawType = params.get("type");
  const country = COUNTRIES.includes(rawCountry as Country) ? (rawCountry as Country) : "all";
  const type = TYPES.includes(rawType as ProjectType) ? (rawType as ProjectType) : "all";

  const update = (key: "country" | "type", value: string) => {
    const next = new URLSearchParams(params);
    if (value === "all") next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
  };

  // Only offer filters that have projects (the empty state stays reachable through the URL).
  const all = data?.projects ?? [];
  const countries = COUNTRIES.filter((c) => all.some((p) => p.country === c));
  const types = TYPES.filter((x) => all.some((p) => p.type === x));
  const list = (data?.projects ?? []).filter((p) => (country === "all" || p.country === country) && (type === "all" || p.type === type));

  return (
    <>
      <section className="page-head">
        <div className="container">
          <h1 className="display">{t.projects.title}</h1>
          <p className="lead">{t.projects.description}</p>
        </div>
      </section>
      <section className="section section--tight-top" style={{ paddingBottom: "var(--section-y)" }}>
        <div className="container">
          <div className="filters" style={{ marginBottom: 48 }}>
            <Segmented
              label={t.filters.country}
              value={country}
              onChange={(v) => update("country", v)}
              options={[{ value: "all" as const, label: t.filters.all }, ...countries.map((v) => ({ value: v, label: t.filters[v] }))]}
            />
            <Segmented
              label={t.filters.type}
              value={type}
              onChange={(v) => update("type", v)}
              options={[{ value: "all" as const, label: t.filters.all }, ...types.map((v) => ({ value: v, label: t.types[v] }))]}
            />
            {data && <span className="caption count" aria-live="polite">{t.projects.count(list.length)}</span>}
          </div>

          {!data && error ? (
            <div className="empty">
              <p>{t.projects.loadError}</p>
              <button className="btn btn--outline" onClick={reload}>↻</button>
            </div>
          ) : !data ? (
            <ProjectGridSkeleton />
          ) : list.length === 0 ? (
            <div className="empty">
              <h2>{t.projects.emptyTitle}</h2>
              <p className="lead">{t.projects.emptySub}</p>
              <button className="btn btn--outline" onClick={() => setParams({}, { replace: true })}>{t.projects.clear}</button>
            </div>
          ) : (
            <div className="grid grid--3">
              {list.map((p) => (
                <ProjectCard key={p.id} p={p} />
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
