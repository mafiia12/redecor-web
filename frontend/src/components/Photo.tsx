import { useEffect, useRef, useState, type CSSProperties } from "react";
import type { Img } from "../lib/api";
import { useData, useLang } from "../lib/context";

interface PhotoProps {
  img?: Img | null;
  alt?: string;
  ratio?: string; // "16/9"
  radius?: number;
  dark?: boolean;
  /** Above-the-fold image: load immediately with high priority. */
  priority?: boolean;
  sizes?: string;
  /** Shown while no real photo has been uploaded yet. */
  hint?: string;
  className?: string;
}

export function Photo({ img, alt = "", ratio = "4/3", radius = 0, dark, priority, sizes = "100vw", className = "" }: PhotoProps) {
  const [loaded, setLoaded] = useState(false);
  const ref = useRef<HTMLImageElement>(null);

  // Cached images can finish before React attaches onLoad.
  useEffect(() => {
    if (ref.current?.complete && ref.current.naturalWidth > 0) setLoaded(true);
  }, [img?.src]);

  // No photo uploaded yet: render nothing (no grey boxes on a live site).
  if (!img) return null;

  const style = { aspectRatio: ratio.replace("/", " / "), borderRadius: radius, "--r": `${radius}px`, backgroundColor: img?.color } as CSSProperties;

  return (
    <div className={`photo${dark ? " photo--dark" : ""} ${className}`} style={style}>
      {(
        <img
          ref={ref}
          src={img.src}
          srcSet={img.srcset}
          sizes={sizes}
          width={img.width}
          height={img.height}
          alt={alt}
          style={img.fx != null && img.fy != null ? { objectPosition: `${img.fx * 100}% ${img.fy * 100}%` } : undefined}
          loading={priority ? "eager" : "lazy"}
          decoding="async"
          // @ts-expect-error fetchpriority is valid HTML but missing from React 18 typings
          fetchpriority={priority ? "high" : "auto"}
          className={loaded ? "is-loaded" : ""}
          onLoad={() => setLoaded(true)}
          onError={() => setLoaded(true)}
        />
      )}
    </div>
  );
}

/** A photo that comes from a named site slot managed in the admin ("home-hero", "service-fitout"...). */
export function SitePhoto({ slot, alt, hideIfEmpty, ...rest }: Omit<PhotoProps, "img"> & { slot: string; hideIfEmpty?: boolean }) {
  const { data } = useData();
  const { lang } = useLang();
  const s = data?.site_images[slot];
  const text = s ? (lang === "ar" && s.alt_ar ? s.alt_ar : s.alt_en) || alt : alt;
  // Big covers/heroes disappear until a real photo is uploaded, rather than showing an empty box.
  if (!s) return null;
  return <Photo img={s?.image} alt={text} {...rest} />;
}
