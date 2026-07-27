// Ported verbatim from dig-dug-portal@5619cbfe1 src/utils/plotUtils.js
// Only the three functions the Variant Sifter renderers actually call.
export function renderDot(CTX, XPOS, YPOS, DOT_COLOR, WIDTH) {
    CTX.fillStyle = DOT_COLOR;
    CTX.lineWidth = 0;
    CTX.beginPath();
    let width = !!WIDTH ? WIDTH : 8;
    CTX.arc(XPOS, YPOS, width, 0, 2 * Math.PI);
    CTX.fill();
}

export function renderDashedLine(CTX, X1, Y1, X2, Y2, WIDTH, COLOR, DASH) {

    CTX.beginPath();
    CTX.lineWidth = !!WIDTH ? WIDTH : 2;
    CTX.strokeStyle = !!COLOR ? COLOR : "#FFAA00";
    let dash = !!DASH ? DASH : [20, 10];
    CTX.setLineDash(dash);
    CTX.moveTo(X1, Y1);
    CTX.lineTo(X2, Y2);
    CTX.stroke();
    // reset
    CTX.setLineDash([]);
}

export function renderStar(CTX, CX, CY, SPIKES, OR, IR, SCOLOR, FCOLOR) {
    let rot = Math.PI / 2 * 3;
    let x = CX;
    let y = CY;
    let step = Math.PI / SPIKES;

    CTX.beginPath();
    CTX.moveTo(CX, CY - OR)
    for (let i = 0; i < SPIKES; i++) {
        x = CX + Math.cos(rot) * OR;
        y = CY + Math.sin(rot) * OR;
        CTX.lineTo(x, y)
        rot += step

        x = CX + Math.cos(rot) * IR;
        y = CY + Math.sin(rot) * IR;
        CTX.lineTo(x, y)
        rot += step
    }
    CTX.lineTo(CX, CY - OR);
    CTX.closePath();
    CTX.lineWidth = 1;
    CTX.strokeStyle = SCOLOR;
    CTX.stroke();
    CTX.fillStyle = FCOLOR;
    CTX.fill();
}

export default { renderDot, renderDashedLine, renderStar };
