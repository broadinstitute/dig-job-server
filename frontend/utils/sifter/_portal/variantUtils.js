// Ported verbatim from dig-dug-portal@5619cbfe1 src/utils/variantUtils.js
const DBSNP_REGEXP = /^rs\d+$/i;
const VARID_REGEXP = /^(\d+|X|Y|MT):(\d+)[:_]([ACGT]+)[:/]([ACGT]+)$/i;

export function parseVariant(variantID) {
    let isDBSNP = variantID.trim().match(DBSNP_REGEXP);
    let isVarId = variantID.trim().match(VARID_REGEXP);

    if (!!isDBSNP) {
        return variantID;
    }

    if (!!isVarId) {
        let chr = isVarId[1].toUpperCase();
        let pos = parseInt(isVarId[2]);
        let ref = isVarId[3].toUpperCase();
        let alt = isVarId[4].toUpperCase();
        return `${chr}:${pos}:${ref}:${alt}`;
    }
}

export function gaitVariant(variantID) {
    let split = variantID.split(":");
    return `${split[0]}:${split[1]}_${split[2]}/${split[3]}`;
}

export default { parseVariant, gaitVariant };
