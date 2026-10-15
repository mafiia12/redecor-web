import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DataProvider, LangProvider } from "./lib/context";
import type { Lang } from "./i18n";
import Home from "./pages/Home";
import NotFound from "./pages/NotFound";

// Everything except Home is split into its own chunk so the first paint ships less JavaScript.
const Projects = lazy(() => import("./pages/Projects"));
const ProjectDetail = lazy(() => import("./pages/ProjectDetail"));
const ServiceDetail = lazy(() => import("./pages/ServiceDetail"));
const Contact = lazy(() => import("./pages/Contact"));
const About = lazy(() => import("./pages/About"));
const Privacy = lazy(() => import("./pages/Misc"));
const Admin = lazy(() => import("./admin/AdminApp"));

function PublicRoutes({ lang }: { lang: Lang }) {
  return (
    <LangProvider lang={lang}>
      <Suspense fallback={<div className="route-loading" />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="projects" element={<Projects />} />
            <Route path="projects/:slug" element={<ProjectDetail />} />
            <Route path="services/:slug" element={<ServiceDetail />} />
            <Route path="about" element={<About />} />
            <Route path="contact" element={<Contact />} />
            <Route path="privacy" element={<Privacy />} />
            <Route path="services" element={<Navigate to="fitout" replace />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </LangProvider>
  );
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/admin/*"
        element={
          <Suspense fallback={null}>
            <Admin />
          </Suspense>
        }
      />
      <Route
        path="/ar/*"
        element={
          <DataProvider>
            <PublicRoutes lang="ar" />
          </DataProvider>
        }
      />
      <Route
        path="/*"
        element={
          <DataProvider>
            <PublicRoutes lang="en" />
          </DataProvider>
        }
      />
    </Routes>
  );
}
