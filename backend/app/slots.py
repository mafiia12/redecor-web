"""Every named image slot the public site uses. The admin lists these so photos can be dropped in later."""

SLOTS: list[tuple[str, str]] = [
    ("home-hero", "Home: hero (landscape, full-bleed)"),
    ("service-design", "Service tile: Interior Design"),
    ("service-fitout", "Service tile: Fine Finishes & Fit-Out"),
    ("service-supply", "Service tile: Supply"),
    ("service-design-hero", "Service page hero: Interior Design"),
    ("service-fitout-hero", "Service page hero: Fine Finishes & Fit-Out"),
    ("service-supply-hero", "Service page hero: Supply"),
    ("service-fitout-d1", "Service detail 1: Fine Finishes & Fit-Out"),
    ("service-fitout-d2", "Service detail 2: Fine Finishes & Fit-Out"),
    ("how-we-work-1", "How we work: Design"),
    ("how-we-work-2", "How we work: Engineering & Procurement"),
    ("how-we-work-3", "How we work: Execution"),
    ("how-we-work-4", "How we work: Handover"),
    ("about-hero", "About: hero"),
]
SLOT_KEYS = {k for k, _ in SLOTS}
