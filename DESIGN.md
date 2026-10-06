# Check8 Design

Professional neobrutalism for a college clearance application. The supplied Check8 logo is the brand authority. Keep the workflows operational: readable records, accessible forms, clear statuses, and fast account access.

## Visual System

- Outfit, self-hosted, is the interface font. Use weights 400-750 and zero letter spacing.
- Use only white and orange shades: white surfaces, orange `#ff822e` actions, deep orange `#632600` text and outlines, and pale orange fills.
- Do not introduce blue, green, yellow, red, gray, or black UI accents. Status labels and border treatments distinguish states within the orange palette.
- Use 2px ink outlines, 3-5px corners, and restrained 3-8px hard offset shadows. Keep page sections unframed; frame controls, tables, identity passes, and forms that need a boundary.
- Primary buttons use orange with deep orange text. Text links and focus rings use darker orange for readable contrast.
- Status always includes a text label. Clearance progress comes from the current user's real course records.

## Brand Assets

`app/static/images/check8-logo.png` is a direct copy of the supplied logo. `.brand-symbol` displays its symbol through a CSS window; the login identity sheet displays the original lockup. Do not replace or redraw the logo with text or generated imagery.

## Implementation

`style.css` owns the shared layout; `neobrutal.css` owns the visual theme and its responsive adjustments. Use Lucide for UI icons. Keep dependencies and fonts local.

Navigation uses native cross-document crossfades (140ms exit, 220ms arrival), preserving normal links, forms, downloads, and browser history. Dashboard tabs use a cancellable 220ms entrance. Keep the logo's brief GSAP entrance; avoid stacking title and section animations on navigation. Content is visible without JavaScript. Disable movement for reduced-motion preferences.

Student clearance records refresh in place every 10 seconds while visible and online. Allow one request at a time, abort after 8 seconds, and back off to 20/40/60 seconds on failures. Pause when hidden or offline; refresh on return. Stop on expired authentication. Never reload the page to poll.

On small screens, login comes before supporting brand content. Administrative tables remain horizontally scrollable and keyboard-focusable; student records use labeled rows. The Add Student form is a native disclosure so the records stay accessible on arrival.
