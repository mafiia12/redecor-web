"""Every named image slot the public site uses. The admin lists these so photos can be dropped in later."""

SLOTS: list[tuple[str, str]] = [
    ("home-hero", "Home: hero (landscape, full-bleed)"),
    ("service-contracting", "Service tile: Contracting"),
    ("service-fitout", "Service tile: Interior Fit-Out"),
    ("service-supply", "Service tile: Procurement & Supply"),
    ("service-project-management", "Service tile: Project Management"),
    ("service-contracting-hero", "Service page hero: Contracting"),
    ("service-fitout-hero", "Service page hero: Interior Fit-Out"),
    ("service-supply-hero", "Service page hero: Procurement & Supply"),
    ("service-project-management-hero", "Service page hero: Project Management"),
    ("service-fitout-d1", "Service detail 1: Interior Fit-Out"),
    ("service-fitout-d2", "Service detail 2: Interior Fit-Out"),
    ("how-we-work-1", "How we work: Design"),
    ("how-we-work-2", "How we work: Engineering & Procurement"),
    ("how-we-work-3", "How we work: Execution"),
    ("how-we-work-4", "How we work: Handover"),
    ("about-hero", "About: hero"),
]
SLOT_KEYS = {k for k, _ in SLOTS}
