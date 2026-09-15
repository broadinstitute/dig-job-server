// Logo strips for the landing page ("proudly supported by") and the GWAS-Hub
// page ("proudly trusted by").
//
// Shape: { name, src?, href? }
//   - name: always shown (alt text, or the label of the placeholder tile)
//   - src:  path under public/, e.g. "/images/partners/hermes.png".
//           When absent, LogoStrip renders a dashed placeholder tile.
//   - href: optional external link wrapped around the logo.
//
// Drop image files into frontend/public/images/partners/ and fill in `src`.

export const FUNDER_LOGOS = [
    { name: "Funder 1" },
    { name: "Funder 2" },
    { name: "Funder 3" },
];

export const PARTNER_LOGOS = [
    { name: "Skin Genetics Consortium" },
    { name: "HERMES" },
];
