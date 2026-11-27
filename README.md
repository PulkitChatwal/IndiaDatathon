# India Datathon website

Static, single-page site. Plain HTML, CSS and JavaScript; no framework and no npm.
Publish the `site/` folder only.

## Folders

| Path | What it is |
| --- | --- |
| `content/event.json` | **The one place to edit facts**: dates, venue, registration state, agenda, faculty, FAQs, sponsors, contacts, form questions. |
| `src/index.template.html` | Section layout and prose (About, Participate wording, headings). |
| `google-form/create-form.gs` | Generated script that creates the participation form as a Google Form. |
| `build.py` | Combines the two files above into `site/index.html`. Python 3 standard library only. |
| `site/` | The finished website. Deploy this folder as it is. |
| `src/form.template.html` | Layout of the separate form page, `site/form.html`, which shows the Google Form inside the site. Built whenever `registration.formUrl` is set. |
| `site/assets/css/site.css` | Colours, type, layout, responsive rules. |
| `site/assets/js/app.js` | Menu, day tabs, show-all buttons, countdown, form behaviour. |
| `_source/` | The original developer package and handoff text, kept for reference. Internal; never publish. Excluded from git by `.gitignore`. |

## Live site

https://indiadatathon.org/ is served by GitHub Pages from the `main` branch of this repository
(`CNAME` holds the domain). The build writes the page twice: `site/index.html` for local work and
`index.html` at the repository root, the copy visitors get at the bare domain (its asset paths point
into `site/assets/`). To publish changes: rebuild, commit, and push `main` (or run `./deploy.sh`).

The domain is registered with Wix; its DNS records at Wix point to GitHub Pages:
four A records for the bare domain (185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153)
and a CNAME record `www` → `pulkitchatwal.github.io`.

## Make a change

1. Edit `content/event.json` (or the template for prose).
2. Run `python3 build.py`.
3. Open `site/index.html`, or run `python3 -m http.server 4173 --directory site` and visit `http://localhost:4173`.

Do not edit `site/index.html` by hand; the next build overwrites it.

The build stops with a clear message if something unsafe would be published: placeholder text
such as `xxx`, a link to a section that does not exist, registration marked open with no form,
or an email form that would discard addresses on a public build.

## Switches in `content/event.json`

| Setting | Values | Effect |
| --- | --- | --- |
| `site.preview` | `true` / `false` | `true` shows the "Design preview" bar and blocks search engines. |
| `site.url` | final address | Adds the canonical link and the share image for WhatsApp/LinkedIn previews. |
| `registration.state` | `upcoming`, `open`, `waitlist`, `closed` | Changes the top bar, hero buttons, nav button, status pill and the form section together. |
| `registration.formUrl` | link | With state `open`: shows a button to an external form (Google Form, Typeform…). |
| `registration.formEndpoint` | address | With state `open`: the built-in form goes live and posts its answers there. |
| `signup.mode` | `off`, `demo`, `live` | `off` removes the email form. `demo` shows it but saves nothing (preview builds only). `live` posts to `signup.endpoint`. |
| `signup.successState` | `pending`, `confirmed` | Which success message matches the email service (double opt-in or immediate). |
| `signup.privacyUrl` | link | Privacy notice link under both forms and in the footer. |
| `contacts.*` | emails | Empty contacts are never shown. Filling `sponsorshipEmail` turns the sponsor note into a button. |
| `event.mapEmbedUrl` | Google Maps address | The live map in the Venue section. Empty = the India Gate drawing is shown instead. |
| `faculty[]` | list | Each person: `name`, `affiliation`, `bio`, `portrait` (file in `site/assets/faculty/`), `linkedin` (leave `""` for none). |
| `sponsors.items` | list | Empty = "Coming soon" tiles. Add `{ "name", "logo", "url", "group" }` entries when confirmed. |
| `form.sections` | list | Questions in the participation form. `"required": false` makes one optional. |

### The participation form (Google Form)

The questions follow the ESICM Datathon 2027 registration form, adapted for this event, and
live in `form.sections`. While `registration.state` is `upcoming` the page shows them as a
locked "Coming soon" preview.

**Create the form once** (about two minutes, in the Google account that should own the answers):

1. Open script.google.com, choose "New project", paste `google-form/create-form.gs`, save.
2. Run `createForm` and approve the Google permission prompt.
3. The execution log prints the link to share, the editor link and the Google Sheet for answers.
   The form is created **closed**, so nobody can answer early.
4. Paste the share link into `registration.formUrl` and rebuild. The page still shows the
   locked preview until the state changes.

**On opening day:**

1. In the same script project run `openRegistration`.
2. Set `registration.state` to `open` and rebuild. The preview is replaced by the Google Form
   shown inside the page, with a button to open it in its own tab
   (`registration.formEmbed: false` gives the button only).

`closeRegistration` stops new answers; then set `registration.state` to `closed`.
The built-in form also works on its own: leave `formUrl` empty and set `formEndpoint` instead.

### Adding sponsors

Put logo files in `site/assets/sponsors/`, add entries to `sponsors.items`, rebuild.
The "Coming soon" badge and the "Soon" tag in the menu disappear automatically.

### Share image

`python3 build.py --og` rebuilds `site/assets/og-image.png` (needs Google Chrome installed).

## Before launch

- [ ] Organizer approval of all public copy and of each faculty name and biography.
- [ ] `site.preview` set to `false`; `site.url` set to the final domain.
- [ ] Email signup connected to an approved service (`signup.mode: "live"`), or switched `off`.
- [ ] Approved privacy notice linked (`signup.privacyUrl`).
- [ ] General and sponsorship contacts filled in.
- [ ] Map pin checked against the real entrance; gate, floor and accessibility details added.
      Google lists the hospital as Jasola Vihar, 110020; the site uses Apollo's official Sarita Vihar, 110076.
- [ ] Privacy notice mentions the embedded Google Map (it loads from Google when the Venue section is reached).
- [ ] Apollo Hospitals' approval to show their logo. The files in `site/assets/logos/` are the official logo, unmodified, from apollohospitals.com.
- [ ] Fee, deadline, admission process, dataset and clinical tracks added when confirmed.
- [ ] Privacy notice names where form answers are stored (Google Forms, in the organizer's account).
- [ ] Checked on a real iPhone (Safari) and Android phone (Chrome), portrait and landscape.

Not confirmed, so not claimed anywhere on the site: international eligibility, CME credits,
team size, selection criteria, prize details, AWS sponsorship.
