from .models import Client, Project, ProjectImage
from .schemas import (
    ClientOut,
    ProjectCardOut,
    ProjectDetailOut,
    ProjectImageOut,
    image_out,
)


def cover_of(p: Project):
    imgs = p.images
    chosen = next((i for i in imgs if i.is_cover), None) or (imgs[0] if imgs else None)
    return chosen


def project_image_out(pi: ProjectImage) -> ProjectImageOut:
    return ProjectImageOut(
        id=pi.id,
        is_cover=pi.is_cover,
        is_render=pi.is_render,
        full_bleed=pi.full_bleed,
        layout=pi.layout,
        caption_en=pi.caption_en,
        caption_ar=pi.caption_ar,
        sort_order=pi.sort_order,
        image=image_out(pi.image),
    )


def card_out(p: Project) -> ProjectCardOut:
    cover = cover_of(p)
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
        is_render=bool(p.is_render or (cover and cover.is_render)),
        featured=p.featured,
        cover=image_out(cover.image) if cover else None,
        tagline_en=p.tagline_en or "",
        tagline_ar=p.tagline_ar or "",
    )


def detail_out(p: Project, related: list[Project], prev: Project | None = None, nxt: Project | None = None) -> ProjectDetailOut:
    gallery = [project_image_out(i) for i in p.images]
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
        scope_en=p.scope_en,
        scope_ar=p.scope_ar,
        gallery=gallery,
        related=[card_out(r) for r in related],
        prev=card_out(prev) if prev else None,
        next=card_out(nxt) if nxt else None,
    )


def client_out(c: Client) -> ClientOut:
    return ClientOut(id=c.id, name=c.name, url=c.url, logo=image_out(c.logo))
