# Deferred and pending content

The website works and looks finished without the items below. Each one is hidden until it is supplied and approved. Nothing here was invented.

## 1. Deferred by the owner (this development cycle)
| Item | Status | What happens meanwhile | How to add it later (no developer needed) |
|---|---|---|---|
| Project photography and architectural renders | **Deferred by owner** | Projects display as typographic tiles and text pages built from published facts. No fake images, no grey boxes. | /admin → Projects → a project → Photos: upload, choose the cover, mark renders, set full/half layout, add captions EN/AR, set the order. Responsive WebP sizes are generated automatically. For bulk import from the company server, use `tools/import_portfolio.py --images-dir` (README). |
| Site images (home hero, services, how-we-work, divisions, about) | **Deferred** | Those sections render without images | /admin → Site images, one slot each |

## 2. Pending company information (owner to confirm)
| Item | Where it shows | Current behaviour |
|---|---|---|
| Qatar office address, phone, hours | Contact, About, WhatsApp | Qatar office hidden; WhatsApp shows one shared number (the owner earlier said Qatar shares Egypt's details). Fill in /admin → Offices. |
| Egypt office opening hours | Contact, About | Hours row hidden until filled |
| "3 regional bases" statistic | About | Hidden (`STAT_CONFIRMED` in `frontend/src/content.ts`); only two offices are listed today |
| Permission to show client logos (especially Fertiglobe / ADNOC) | Home → Clients | New and imported logos start unpublished. The 16 logos already imported into the owner's local database are published there: confirm, or unpublish in /admin → Clients. |
| Real projects to publish (names, cities, years, scope, summaries) | Projects | The manifest has 59 candidates. Open naming questions: Park St Mall / Be Babel, Downtown Hotel / Sheraton, Zayed Mall / Zayed Administrative Building, Sokkar vs Sukkar, The Shield / Global Exchange. Publish only after review. |
| Execution & Fit-Out division lead | Divisions | Shows "Team details coming soon" |
| Company profile PDF | Footer download link | Hidden until uploaded **and** published (/admin → Documents) |
| Client testimonials | Home | Section hidden until a quote is entered with the client's approval recorded and published (/admin → Testimonials) |
| Case-study metrics, certifications, awards | — | Not built as separate features, and nothing is invented. Verified facts can be added per project in "Details" (Label: Value lines). |
| SMTP credentials and the notification recipient address | Enquiry e-mails | Enquiries are saved and marked "E-mail not configured"; delivery starts automatically once configured |
| Domain DNS and hosting account | — | Not changed. See DEPLOYMENT_GUIDE.md |

## 3. Editorial translations missing (Arabic)
The interface is fully translated. Factual project texts are company content and were **not** machine-translated. When an Arabic field is empty, the English text is shown, marked `lang="en" dir="ltr"` so it aligns correctly. Fill these per project in /admin:
- `title_ar`, `city_ar`, `summary_ar`, `tagline_ar`, `story_ar`, `details_ar`, `scope_ar`
- image captions (`caption_ar`)

## 4. Copy the design review flagged (company-written, kept unchanged)
- **Service taglines:** "Built with precision.", "Crafted to perfection.", "Quality in every selection.", "Seamless from start to finish."
- **Contact headline:** "Let's Build Something Exceptional."
- **About:** the vision sentence and the How-We-Work paragraphs

They can be replaced with concrete scope statements once the company approves new wording (`frontend/src/i18n.ts`).
