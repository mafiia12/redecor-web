import { useEffect, useRef, type RefObject } from "react";

export const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Fade-and-rise on scroll. Elements stay visible if JS or IntersectionObserver is unavailable. */
let observer: IntersectionObserver | null = null;
function getObserver(): IntersectionObserver | null {
  if (typeof IntersectionObserver === "undefined" || prefersReducedMotion()) return null;
  observer ??= new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          observer?.unobserve(e.target);
        }
      }
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.05 },
  );
  return observer;
}

export function useReveal<T extends HTMLElement>(): RefObject<T> {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    const io = getObserver();
    if (!el || !io) return;
    el.classList.add("reveal");
    io.observe(el);
    return () => io.unobserve(el);
  }, []);
  return ref;
}

/** Slowly scales the hero image from 1.08 to 1 while the page scrolls. */
export function useHeroScale<T extends HTMLElement>(): RefObject<T> {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return;
    let raf = 0;
    const update = () => {
      raf = 0;
      const p = Math.min(1, Math.max(0, window.scrollY / 700));
      el.style.setProperty("--hero-scale", String(1.08 - 0.08 * p));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);
  return ref;
}
