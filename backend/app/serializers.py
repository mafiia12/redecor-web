from .models import Client, Project, ProjectImage
from .schemas import (
    ClientOut,
    ProjectCardOut,
    ProjectDetailOut,
    ProjectImageAdminOut,
    ProjectImageOut,
    image_out,
)


def cover_of(p: Project, public: bool = False):
    imgs = public_images(p) if public else p.images
    chosen = next((i for i in imgs if i.is_cover), None) or (imgs[0] if imgs else None)
    return chosen


def public_images(p: Project) -> list[ProjectImage]:
    """Only images labelled render/executed are ever shown publicly (visitors must know what they look at)."""
    return [i for i in p.images if i.kind in ("render", "executed")]


def focal_image_out(pi: ProjectImage):
    out = image_out(pi.image)
    if out is not None:
        out.fx = pi.focal_x if pi.focal_x is not None else 0.5
        out.fy = pi.focal_y if pi.focal_y is not None else 0.5
    return out


def project_image_out(pi: ProjectImage, admin: bool = False) -> ProjectImageOut:
    extra = dict(focal_x=pi.focal_x, focal_y=pi.focal_y, quality_warnings=pi.quality_warnings or "",
                 quality_override_by=pi.quality_override_by or "") if admin else {}
    return (ProjectImageAdminOut if admin else ProjectImageOut)(
        id=pi.id,
        is_cover=pi.is_cover,
        is_render=(pi.kind == "render") if pi.kind else pi.is_render,
        full_bleed=pi.full_bleed,
        layout=pi.layout,
        caption_en=pi.caption_en,
        caption_ar=pi.caption_ar,
        sort_order=pi.sort_order,
        image=focal_image_out(pi),
        kind=pi.kind,
        alt_en=pi.alt_en or "",
        alt_ar=pi.alt_ar or "",
        **extra,
    )


def card_out(p: Project) -> ProjectCardOut:
    cover = cover_of(p, public=True)
    return ProjectCardOut(
        id=p.id,
        slug=p.slug,
        title_en=p.title_en,
        title_ar=p.title_ar,
        city_en=p.city_en,
        city_ar=p.city_ar,
        country=p.country,
        type=p.type,
        year=p.year,
        is_render=bool(p.is_render or (cover and cover.kind == "render")),
        featured=p.featured,
        cover=focal_image_out(cover) if cover else None,
        tagline_en=p.tagline_en or "",
        tagline_ar=p.tagline_ar or "",
        scope_en=p.scope_en or "",
        scope_ar=p.scope_ar or "",
    )


def detail_out(p: Project, related: list[Project], prev: Project | None = None, nxt: Project | None = None) -> ProjectDetailOut:
    gallery = [project_image_out(i) for i in public_images(p)]
    return ProjectDetailOut(
        **card_out(p).model_dump(),
        summary_en=p.summary_en,
        summary_ar=p.summary_ar,
        story_en=p.story_en,
        story_ar=p.story_ar,
        details_en=p.details_en,
        details_ar=p.details_ar,
        client_name=p.client_name,
        logo=image_out(p.logo),
        area_m2=p.area_m2,
        gallery=gallery,
        related=[card_out(r) for r in related],
        prev=card_out(prev) if prev else None,
        next=card_out(nxt) if nxt else None,
    )


def client_out(c: Client) -> ClientOut:
    return ClientOut(id=c.id, name=c.name, url=c.url, logo=image_out(c.logo))
