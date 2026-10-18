"""Every named image slot the public site uses. The admin lists these so photos can be dropped in later."""

SLOTS: list[tuple[str, str]] = [
    ("home-hero", "Home: hero (landscape, full-bleed)"),
    ("projects-hero", "Projects page: dark background photo behind the title (optional; defaults to a project cover)"),
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
    ("how-we-work-1", "How we work: Planning & Budgeting"),
    ("how-we-work-2", "How we work: Design & Development"),
    ("how-we-work-3", "How we work: Execution & Close-Out"),
    ("division-design", "Our divisions: Interior Design (render, landscape)"),
    ("division-execution", "Our divisions: Execution & Fit-Out (site photo, landscape)"),
    ("division-contracting", "Our divisions: Contracting & Commercial (landscape)"),
    ("division-bd", "Our divisions: Business Development (landscape)"),
    ("about-hero", "About: tall photo beside the text (portrait works best)"),
]
SLOT_KEYS = {k for k, _ in SLOTS}
