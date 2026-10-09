// Logo strips for the landing page ("proudly supported by") and the GWAS-Hub
// page ("proudly trusted by").
//
// Shape: { name, fullName?, src?, href? }
//   - name: always shown (alt text, or the label of the placeholder tile)
//   - fullName: optional expanded name, shown on the GWAS-Hub partner cards
//   - src:  path under public/, e.g. "/images/partners/hermes.png".
//           When absent, LogoStrip renders a dashed placeholder tile.
//   - href: optional external link wrapped around the logo.
//   - website: optional consortium homepage, linked from the GWAS-Hub
//           partner cards.
//   - bgClass: optional Tailwind classes for a panel behind the logo, for
//           artwork with white text that expects a coloured background.
//
// Drop image files into frontend/public/images/partners/ and fill in `src`.

export const FUNDER_LOGOS = [
    { name: "Funder 1" },
    { name: "Funder 2" },
    { name: "Funder 3" },
];

export const PARTNER_LOGOS = [
    {
        name: "Skin Genetics Consortium",
        src: "/images/partners/skin-genetics-consortium.svg",
        href: "https://kpndataregistry.org/sgc",
        website: "https://skingeneticsconsortium.org/",
        // The SVG's wordmark is white with no background rect; give it the
        // blue panel it was designed for.
        //bgClass: "rounded-md bg-[#2e6db4] px-4 py-2",
    },
    {
        name: "HERMES",
        fullName:
            "Heart Failure Molecular Epidemiology for Therapeutic Targets",
        src: "/images/partners/hermes.png",
        href: "https://kpndataregistry.org/hermes",
        website: "https://www.hermesconsortium.org/",
        //bgClass: "rounded-md bg-[#313a7e] px-4 py-2",
    },
];
