import { Link } from "react-router-dom";
import { useLang, usePageMeta } from "../lib/context";

export default function NotFound() {
  const { t, lp } = useLang();
  usePageMeta(`${t.notFound.title} | ${t.brand}`);
  return (
    <div className="container notice">
      <h1 className="display">404</h1>
      <h2 className="h3">{t.notFound.title}</h2>
      <p className="lead">{t.notFound.sub}</p>
      <Link to={lp("/")} className="btn">{t.notFound.home}</Link>
    </div>
  );
}
