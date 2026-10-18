import type { CSSProperties } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ProjectGridSkeleton, ProjectTile } from "../components/Cards";
import { WorkHero } from "../components/WorkHero";
import { Segmented } from "../components/Filters";
import { useData, useLang, usePageMeta } from "../lib/context";
import type { Country, ProjectType } from "../lib/api";

const TYPES: ProjectType[] = ["residential", "hospitality", "retail", "office", "industrial", "healthcare", "public", "education", "landscape"];
const COUNTRIES: Country[] = ["eg", "qa", "sa"];

export default function Projects() {
  const { t, lp } = useLang();
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
  const q = (params.get("q") ?? "").trim();
  const needle = q.toLowerCase();
  const matches = (p: (typeof all)[number]) =>
    !needle ||
    [p.title_en, p.title_ar, p.city_en, p.city_ar, p.tagline_en, p.tagline_ar, t.types[p.type], t.countries[p.country]]
      .some((v) => v?.toLowerCase().includes(needle));
  const list = all.filter((p) => (country === "all" || p.country === country) && (type === "all" || p.type === type) && matches(p));
  const setQuery = (value: string) => {
    const next = new URLSearchParams(params);
    if (value.trim()) next.set("q", value);
    else next.delete("q");
    setParams(next, { replace: true });
  };

  return (
    <>
      <WorkHero title={t.home.workTitle} sub={t.projects.description} bg={data?.site_images["projects-hero"]?.image ?? all.find((p) => p.cover)?.cover} target="work-grid" compact />
      <section className="section" id="work-grid" style={{ paddingBlock: "56px 96px" }}>
        <div className="container">
          {all.length > 0 && (
          <div className="filters" style={{ marginBottom: 32 }}>
            {countries.length > 1 && <Segmented
              label={t.filters.country}
              value={country}
              onChange={(v) => update("country", v)}
              options={[{ value: "all" as const, label: t.filters.all }, ...countries.map((v) => ({ value: v, label: t.filters[v] }))]}
            />}
            <Segmented
              label={t.filters.type}
              value={type}
              onChange={(v) => update("type", v)}
              options={[{ value: "all" as const, label: t.filters.all }, ...types.map((v) => ({ value: v, label: t.types[v] }))]}
            />
            {all.length > 6 && (
              <label className="search">
                <span className="sr-only">{t.projects.search}</span>
                <input type="search" className="search__input" placeholder={t.projects.searchPh} value={q} onChange={(e) => setQuery(e.target.value)} maxLength={60} />
              </label>
            )}
            {data && <span className="caption count" aria-live="polite">{t.projects.count(list.length)}</span>}
          </div>
          )}

          {!data && error ? (
            <div className="empty">
              <p>{t.projects.loadError}</p>
              <button className="btn btn--outline" onClick={reload}>↻</button>
            </div>
          ) : !data ? (
            <ProjectGridSkeleton />
          ) : all.length === 0 ? (
            <div className="empty">
              <h2>{t.projects.soonTitle}</h2>
              <p className="lead">{t.projects.soonSub}</p>
              <Link to={lp("/contact")} className="btn">{t.cta}</Link>
            </div>
          ) : list.length === 0 ? (
            <div className="empty">
              <h2>{t.projects.emptyTitle}</h2>
              <p className="lead">{t.projects.emptySub}</p>
              <button className="btn btn--outline" onClick={() => setParams({}, { replace: true })}>{t.projects.clear}</button>
            </div>
          ) : (
            <div className="mosaic" style={{ "--n": list.length } as CSSProperties}>
              {list.map((p) => (
                <ProjectTile key={p.id} p={p} />
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
