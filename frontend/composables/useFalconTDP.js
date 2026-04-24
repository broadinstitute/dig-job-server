// frontend/composables/useFalconTDP.js
// Port of TDPModule (PEGS/src/dashboard/app.js:1842-2507).
// Entry point: runAnalysis(cfg) returns a Plotly {data, layout} spec.
//
// Substitution rules (documented in plan Task 15):
// - DataStore.* / FileLoader.ldFiles → store.*
// - ColorManager → getColorForClump / FALCON_PALETTE
// - No DOM touched; returns spec for the component to mount
// - Respects store.globalFilter at run-analysis time only (spec §11 preserved quirk)
//
// Notes on fidelity:
// - The original TDPModule pulled per-chromosome variant/v2g trait files from
//   FileLoader.rawFiles (the whole folder the user originally selected) and
//   the .ld chunk files from FileLoader.ldFiles. In this port both live in
//   store.tdp.ldFiles — the plan's substitution table maps ldFiles → tdp.ldFiles,
//   and there is no separate mapping for rawFiles. Treating the LD folder as
//   the source for both .variants/.v2g/.ld trait files matches the
//   "tdp file bundle" pattern the user loads via loadLdFolder(). If the
//   per-chr trait files live elsewhere, the discovery regex below still works
//   over whatever FileList is stored there.
// - LD chunk cache: original used TDPModule.ldCache (a plain object keyed by
//   `chr${chr}_${bin}`). Port uses store.caches.ldBinCache (a Map, same keys).
import Papa from "papaparse";
import { readGzippedText } from "~/utils/falcon/pako";
import { getColorForClump, FALCON_PALETTE } from "~/utils/falcon/colorPalette";

export function useFalconTDP(store) {
  // ----- helpers (inside closure, as original did) -----

  // Parse a .variants / .v2g tab-delimited trait file, optionally filtered row-by-row.
  // Mirrors TDPModule.parseSpecificFile (app.js:1854-1873).
  function parseSpecificFile(file, filterFn = null) {
    return new Promise((resolve, reject) => {
      if (!file) {
        resolve([]);
        return;
      }
      const data = [];
      Papa.parse(file, {
        header: true,
        skipEmptyLines: true,
        delimiter: "\t",
        step: function (row) {
          if (row && row.data) {
            if (!filterFn || filterFn(row.data)) {
              data.push(row.data);
            }
          }
        },
        complete: () => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  // Parse an LD chunk file (optionally gzipped). Mirrors TDPModule.loadLDChunk
  // (app.js:1875-1915). Results cached in store.caches.ldBinCache by chunkKey.
  async function loadLDChunk(file, chunkKey) {
    if (store.caches.ldBinCache.has(chunkKey)) {
      console.log(`[LD Debug] Cache hit for chunk ${chunkKey}.`);
      return store.caches.ldBinCache.get(chunkKey);
    }

    console.log(`[LD Debug] Parsing tiny LD chunk: ${file.name}`);
    const dataArray = [];

    // Support .ld.gz (inflate → text → Papa.parse(string)) and plain .ld
    // (Papa.parse(file, stream)). Both cases end with the same row shape.
    const handleRow = (data) => {
      if (!data) return;
      const bpA = parseInt(data["BP_A"]);
      const bpB = parseInt(data["BP_B"]);
      const r2 = parseFloat(data["R2"]);
      if (!isNaN(bpA) && !isNaN(bpB) && !isNaN(r2)) {
        dataArray.push({
          bpA: bpA,
          bpB: bpB,
          snpA: data["SNP_A"],
          snpB: data["SNP_B"],
          r2: r2,
        });
      }
    };

    if (file.name.endsWith(".gz")) {
      const text = await readGzippedText(file);
      await new Promise((resolve, reject) => {
        Papa.parse(text, {
          header: true,
          skipEmptyLines: true,
          delimiter: "\t",
          step: function (row) {
            if (row && row.data) handleRow(row.data);
          },
          complete: () => resolve(),
          error: (err) => reject(err),
        });
      });
    } else {
      await new Promise((resolve, reject) => {
        Papa.parse(file, {
          header: true,
          skipEmptyLines: true,
          delimiter: "\t",
          step: function (row) {
            if (row && row.data) handleRow(row.data);
          },
          complete: () => resolve(),
          error: (err) => reject(err),
        });
      });
    }

    store.caches.ldBinCache.set(chunkKey, dataArray);
    return dataArray;
  }

  // Binary search for the first LD row whose bpA <= targetBP, scanning a
  // descending-by-bpA array. Mirrors TDPModule.findStartIndex (app.js:1917-1932).
  function findStartIndex(arr, targetBP) {
    let left = 0;
    let right = arr.length - 1;
    let result = -1;

    while (left <= right) {
      const mid = Math.floor((left + right) / 2);
      if (arr[mid].bpA <= targetBP) {
        result = mid;
        right = mid - 1;
      } else {
        left = mid + 1;
      }
    }
    return result === -1 ? arr.length : result;
  }

  function setStatus(msg) {
    store.tdp.status = msg;
  }

  // ----- main entry point -----
  async function runAnalysis(cfg) {
    const {
      gene: targetGeneInput = "",
      boundary = 500000,
      focus = "region",
      plotType = "falcon",
      minR2 = 0.0,
      maxStretch = 1.0,
    } = cfg || {};

    try {
      console.log(`\n--- [LD Debug] STARTING NEW ANALYSIS ---`);

      console.log(`[LD Debug] Step 1: Reading inputs...`);
      if (!targetGeneInput || !String(targetGeneInput).trim()) {
        setStatus("Error: Target Gene is required.");
        return null;
      }
      const trimmedGene = String(targetGeneInput).trim();
      setStatus(`Searching genome for ${trimmedGene}...`);

      console.log(`[LD Debug] Step 2: Accessing store for Genes...`);
      const allGenes = store.datasets.genes.data || [];
      if (!allGenes || allGenes.length === 0) {
        setStatus("Error: Genes dataset not loaded. Please select your folder again.");
        return null;
      }

      console.log(`[LD Debug] Step 3: Finding Target Gene...`);
      const targetGeneUpper = trimmedGene.toUpperCase();
      const geneRow = allGenes.find(
        (r) => (r["GENE"] || r["ID"] || "").toUpperCase() === targetGeneUpper,
      );
      if (!geneRow) {
        setStatus(`Error: Gene '${trimmedGene}' not found.`);
        return null;
      }

      const chr = geneRow["CHR"] ? geneRow["CHR"].toString().trim() : "";
      const targetGene = geneRow["GENE"] || geneRow["ID"];
      if (!chr) {
        setStatus(`Error: Chromosome data missing for gene ${targetGene}.`);
        return null;
      }

      console.log(`[LD Debug] Step 4: Calculating Boundaries...`);
      const plotStart = parseInt(geneRow["START"]) - boundary;
      const plotEnd = parseInt(geneRow["END"]) + boundary;
      console.log(
        `[LD Debug] Window calculated: Chr ${chr} | Start: ${plotStart} | End: ${plotEnd}`,
      );

      let genesToPlot = [];
      if (focus === "gene") {
        genesToPlot.push(geneRow);
      } else {
        genesToPlot = allGenes.filter((r) => {
          const rChr = r["CHR"] ? r["CHR"].toString().trim() : "";
          if (rChr !== chr) return false;
          const s = parseInt(r["START"]);
          const e = parseInt(r["END"]);

          const p = parseFloat(r["PROBABILITY"]);
          const negP = parseFloat(r["NEG_LOG_P"]);

          // Apply Global Filters to Genes (preserved quirk: read at run time only)
          if (store.globalFilter.active) {
            if (
              isNaN(p) ||
              p < store.globalFilter.minProb ||
              isNaN(negP) ||
              negP < store.globalFilter.minNegP
            )
              return false;
          } else {
            // Base fallback to prevent extreme lagging if global filter is off
            if (isNaN(p) || p < 0.01) return false;
          }

          return s <= plotEnd && e >= plotStart;
        });
      }

      if (genesToPlot.length === 0) {
        setStatus(
          `No genes met the strict global criteria in Chr ${chr}:${plotStart}-${plotEnd}.`,
        );
        return null;
      }

      // Per-gene colors from the FALCON palette (original used ColorManager.palette).
      const geneColors = {};
      genesToPlot.forEach((g, i) => {
        const gName = g["GENE"] || g["ID"];
        geneColors[gName] = FALCON_PALETTE[i % FALCON_PALETTE.length];
      });

      setStatus(`Scanning region Chr ${chr}:${plotStart}-${plotEnd}...`);

      console.log(`[LD Debug] Step 5: Accessing store.tdp.ldFiles...`);
      const files = store.tdp.ldFiles || [];
      if (files.length === 0) {
        setStatus(
          `Error: Files lost from memory. Please select the folder again.`,
        );
        return null;
      }

      // Per-chromosome trait file discovery (same regex logic as original,
      // app.js:2044-2055). Try chr-specific match first, fall back to
      // .wg.<ext> / .<ext>.
      const getFile = (ext, exactChr) => {
        let f = files.find((file) => {
          const n = file.name;
          if (exactChr) {
            const chrRegex = new RegExp(
              `(^|[^a-zA-Z0-9])(chr)?${chr}([^a-zA-Z0-9]|$)`,
              "i",
            );
            if (!chrRegex.test(n)) return false;
          }
          return n.endsWith(ext);
        });
        if (!f)
          f = files.find(
            (file) =>
              file.name.endsWith(`.wg.${ext}`) || file.name.endsWith(`.${ext}`),
          );
        return f;
      };

      const fVars = getFile("variants", true) || getFile("variants", false);
      const fV2G = getFile("v2g", true) || getFile("v2g", false);
      if (!fVars) {
        setStatus(`Error: Could not find variants file for Chr ${chr}.`);
        return null;
      }

      console.log(`[LD Debug] Step 6: Processing GWAS/V2G Variants Data...`);
      const processTrait = async (fVars, fV2G) => {
        if (!fVars) return null;

        const rawV2G = fV2G
          ? await parseSpecificFile(fV2G, (row) => {
              return genesToPlot.some(
                (g) => (g["GENE"] || g["ID"]) === row["GENE"],
              );
            })
          : [];

        const linkedToGene = {};
        genesToPlot.forEach((g) => {
          linkedToGene[g["GENE"] || g["ID"]] = new Set();
        });

        rawV2G.forEach((row) => {
          const gName = row["GENE"] || "";
          if (linkedToGene[gName]) {
            linkedToGene[gName].add(
              row["VARIANT"] || row["SNP"] || row["RSID"],
            );
          }
        });

        const tracesData = {
          raw: { x: [], y: [], text: [] },
          unlinked: { x: [], y: [], text: [], symbols: [], sizes: [] },
          genes: {},
          clumps: new Map(),
          validRsids: new Set(),
          validBPs: new Set(),
        };
        genesToPlot.forEach((g) => {
          tracesData.genes[g["GENE"] || g["ID"]] = {
            x: [],
            y: [],
            text: [],
            symbols: [],
            sizes: [],
          };
        });

        const rawVars = await parseSpecificFile(fVars, (row) => {
          const rChr = row["CHR"]
            ? row["CHR"].toString().trim().replace(/^chr/i, "")
            : "";
          const targetChr = chr.replace(/^chr/i, "");
          if (rChr && rChr !== targetChr) return false;
          const pos = parseInt(row["POS"]);
          return pos >= plotStart && pos <= plotEnd;
        });

        rawVars.forEach((row) => {
          const pos = parseInt(row["POS"]);
          const rsid =
            row["VARIANT"] || row["RSID"] || row["SNP"] || `Pos:${pos}`;

          if (row["RSID"]) tracesData.validRsids.add(row["RSID"]);
          if (row["VARIANT"]) tracesData.validRsids.add(row["VARIANT"]);
          if (row["SNP"]) tracesData.validRsids.add(row["SNP"]);

          const leadVal = String(row["LEAD_SNP"] || "").toLowerCase().trim();
          const isLead =
            leadVal === "true" || leadVal === "1" || leadVal === "yes";

          const clumpStr = row["CLUMP"];
          let clumpLabel = "";
          if (clumpStr && String(clumpStr).trim() !== "") {
            const c = String(clumpStr).trim();
            clumpLabel = `<br><b>Clump:</b> ${c}`;

            const parts = c.split("_");
            if (parts.length >= 3) {
              const cStart = parseInt(parts[1]);
              const cEnd = parseInt(parts[2]);
              if (!isNaN(cStart) && !isNaN(cEnd))
                tracesData.clumps.set(c, {
                  start: cStart,
                  end: cEnd,
                  id: c,
                });
            }
          }

          const gwasPStr =
            row["GWAS_P"] || row["P"] || row["PVALUE"] || row["P_VALUE"];
          const gwasP = parseFloat(gwasPStr);
          if (!isNaN(gwasP) && gwasP > 0) {
            const rawNegP = -Math.log10(gwasP);
            const rawHover = `<b>${rsid}</b>${clumpLabel}<br>Pos: ${pos}<br>GWAS_P: ${gwasP.toExponential(
              2,
            )}<br>Neg_Log_P: ${rawNegP.toFixed(2)}<br>Z: ${
              row["GWAS_Z"] || "N/A"
            }<br>BETA: ${row["GWAS_BETA"] || "N/A"}`;
            tracesData.raw.x.push(pos);
            tracesData.raw.y.push(rawNegP);
            tracesData.raw.text.push(rawHover);
            tracesData.validBPs.add(pos);
          }

          const prob = parseFloat(row["PROBABILITY"]);
          let negP = parseFloat(row["NEG_LOG_P"]);
          if (isNaN(negP)) {
            let pVal = parseFloat(row["P_VALUE"]);
            if (!isNaN(pVal) && pVal > 0) negP = -Math.log10(pVal);
          }

          // Apply Global Filters to Variants
          let isSignificant = false;
          if (store.globalFilter.active) {
            if (
              !isNaN(prob) &&
              prob >= store.globalFilter.minProb &&
              !isNaN(negP) &&
              negP >= store.globalFilter.minNegP
            ) {
              isSignificant = true;
            }
          } else {
            // Base fallback
            if (!isNaN(prob) && prob >= 0.01) isSignificant = true;
          }

          if (isSignificant && !isNaN(negP)) {
            let extraBadges = isLead ? "<br><b>⭐ Lead SNP</b>" : "";
            const hoverText = `<b>${rsid}</b>${extraBadges}${clumpLabel}<br>Pos: ${pos}<br>Prob: ${prob}<br>NegP: ${negP.toFixed(
              2,
            )}`;
            let foundLink = false;

            for (const g of genesToPlot) {
              const gName = g["GENE"] || g["ID"];
              let pythonLinked = false;
              for (let i = 1; i <= 3; i++) {
                if (
                  row[`GENE_${i}`] === gName &&
                  parseFloat(row[`LINK_SC_${i}`]) >= 0.1
                ) {
                  pythonLinked = true;
                  break;
                }
              }

              if (linkedToGene[gName].has(rsid) || pythonLinked) {
                tracesData.genes[gName].x.push(pos);
                tracesData.genes[gName].y.push(negP);
                tracesData.genes[gName].text.push(
                  hoverText + `<br>Linked to: <b>${gName}</b>`,
                );
                tracesData.genes[gName].symbols.push(
                  isLead ? "star" : "circle",
                );
                tracesData.genes[gName].sizes.push(isLead ? 16 : 9);
                tracesData.validBPs.add(pos);
                foundLink = true;
                break;
              }
            }

            if (!foundLink) {
              tracesData.unlinked.x.push(pos);
              tracesData.unlinked.y.push(negP);
              tracesData.unlinked.text.push(hoverText);
              tracesData.unlinked.symbols.push(isLead ? "star" : "circle");
              tracesData.unlinked.sizes.push(isLead ? 14 : 6);
              tracesData.validBPs.add(pos);
            }
          }
        });
        return tracesData;
      };

      const tData = await processTrait(fVars, fV2G);
      console.log(`[LD Debug] Step 7: Checking Extracted Variants...`);
      console.log(
        `[LD Debug] Total valid RSIDs collected: ${tData.validRsids.size}`,
      );

      let overlapWarning = "";
      if (tData && tData.clumps.size > 0) {
        const clumpList = Array.from(tData.clumps.values()).sort(
          (a, b) => a.start - b.start,
        );
        for (let i = 1; i < clumpList.length; i++) {
          if (clumpList[i].start <= clumpList[i - 1].end) {
            overlapWarning = " ⚠️ Warning: Overlapping clumps detected.";
            break;
          }
        }
      }

      // =========================================================
      // STEP 8: SMART SHARD FETCHING & DYNAMIC BUMPERS
      // =========================================================
      console.log(`[LD Debug] Step 8: Initializing Smart LD Chunk Fetching...`);
      let ldTrace = null;
      let hasLD = false;

      let stretchValue = parseFloat(maxStretch);
      if (isNaN(stretchValue)) stretchValue = 1.0;
      if (stretchValue < 0.1) stretchValue = 0.1;

      console.log(`[LD Debug] Max Stretch Slider Value: ${stretchValue}`);

      if (store.tdp.ldFiles && store.tdp.ldFiles.length > 0) {
        const CHUNK_SIZE = 1000000;
        const startBin = Math.floor(plotStart / CHUNK_SIZE) * CHUNK_SIZE;
        const endBin = Math.floor(plotEnd / CHUNK_SIZE) * CHUNK_SIZE;

        console.log(
          `[LD Debug] Plot requires chunks from ${startBin} to ${endBin}`,
        );

        let combinedLD = [];
        let filesFound = 0;

        for (let bin = startBin; bin <= endBin; bin += CHUNK_SIZE) {
          const binEnd = bin + CHUNK_SIZE;
          // Original regex requires literal .ld$ — but support .ld.gz too by
          // accepting either tail. Original behavior for .ld still identical.
          const expectedRegex = new RegExp(
            `(^|[^a-zA-Z0-9])(chr)?${chr}_${bin}_${binEnd}\\.ld(\\.gz)?$`,
            "i",
          );

          const chunkFile = store.tdp.ldFiles.find((f) =>
            expectedRegex.test(f.name),
          );

          if (chunkFile) {
            filesFound++;
            const chunkKey = `chr${chr}_${bin}`;
            try {
              const chunkData = await loadLDChunk(chunkFile, chunkKey);
              combinedLD = combinedLD.concat(chunkData);
            } catch (err) {
              console.error(
                `[LD Debug] Error loading chunk ${chunkFile.name}:`,
                err,
              );
            }
          }
        }

        if (combinedLD.length > 0) {
          console.log(
            `[LD Debug] Successfully assembled ${filesFound} chunks. Total rows to scan: ${combinedLD.length}`,
          );
          setStatus(
            `Executing Fast LD Scan (R2 >= ${minR2}) for Chr ${chr}...`,
          );

          combinedLD.sort((a, b) => b.bpA - a.bpA);

          const rawBPs = Array.from(tData.validBPs).sort((a, b) => a - b);

          const plotWidth = plotEnd - plotStart;
          const maxAllowedStretch = plotWidth * 0.05;
          const R = Math.max(10, maxAllowedStretch * stretchValue);

          let axisBPs = [];

          if (rawBPs.length > 0) {
            axisBPs.push(rawBPs[0] - R);
            for (let i = 0; i < rawBPs.length; i++) {
              axisBPs.push(rawBPs[i]);
              if (i < rawBPs.length - 1) {
                const dist = rawBPs[i + 1] - rawBPs[i];
                if (dist > 2 * R) {
                  axisBPs.push(rawBPs[i] + R);
                  axisBPs.push(rawBPs[i + 1] - R);
                }
              }
            }
            axisBPs.push(rawBPs[rawBPs.length - 1] + R);
          }

          const N = axisBPs.length;
          const bpToIndex = new Map(axisBPs.map((bp, i) => [bp, i]));
          const zMatrix = Array(N)
            .fill(null)
            .map(() => Array(N).fill(0.0));
          const textMatrix = Array(N)
            .fill(null)
            .map(() => Array(N).fill("No Data (White Space)"));

          const startIndex = findStartIndex(combinedLD, plotEnd);
          let mappedCount = 0;

          for (let i = startIndex; i < combinedLD.length; i++) {
            const row = combinedLD[i];
            if (row.bpA < plotStart) break;

            if (row.bpB >= plotStart && row.bpB <= plotEnd) {
              if (
                row.r2 >= minR2 &&
                tData.validRsids.has(row.snpA) &&
                tData.validRsids.has(row.snpB)
              ) {
                if (bpToIndex.has(row.bpA) && bpToIndex.has(row.bpB)) {
                  const idxA = bpToIndex.get(row.bpA);
                  const idxB = bpToIndex.get(row.bpB);

                  zMatrix[idxA][idxB] = row.r2;
                  zMatrix[idxB][idxA] = row.r2;

                  const hoverStr = `<b>SNP A:</b> ${row.snpA} (${row.bpA})<br><b>SNP B:</b> ${row.snpB} (${row.bpB})<br><b>R2:</b> ${row.r2.toFixed(
                    3,
                  )}`;
                  textMatrix[idxA][idxB] = hoverStr;
                  textMatrix[idxB][idxA] = hoverStr;
                  mappedCount++;
                }
              }
            }
          }

          if (N > 0) {
            const discreteColorscale = [
              [0.0, "#ffffff"],
              [0.0001, "#ffffff"],
              [0.0001, "#1e3a8a"],
              [0.2, "#1e3a8a"],
              [0.2, "#7dd3fc"],
              [0.4, "#7dd3fc"],
              [0.4, "#fcd34d"],
              [0.6, "#fcd34d"],
              [0.6, "#f97316"],
              [0.8, "#f97316"],
              [0.8, "#ef4444"],
              [1.0, "#ef4444"],
            ];

            ldTrace = {
              x: axisBPs,
              y: axisBPs,
              z: zMatrix,
              text: textMatrix,
              type: "heatmap",
              xaxis: "x",
              yaxis: "y2",
              name: "LD Correlation",
              hoverinfo: "text",
              colorscale: discreteColorscale,
              zmin: 0,
              zmax: 1,
              showscale: true,
              colorbar: {
                title: "R²",
                thickness: 15,
                len: 0.35,
                y: 0.17,
                tickvals: [0, 0.2, 0.4, 0.6, 0.8, 1.0],
              },
            };
            hasLD = true;
          }
        } else {
          console.log(
            "[LD Debug] No matching LD chunk files found for this region in the loaded folder.",
          );
        }
      }

      console.log(`[LD Debug] Step 9: Rendering Subplots...`);
      setStatus(`Rendering Unified Subplots...${overlapWarning}`);
      const traces = [];

      if (plotType === "raw" || plotType === "overlay") {
        if (tData.raw.x.length > 0) {
          traces.push({
            x: tData.raw.x,
            y: tData.raw.y,
            text: tData.raw.text,
            name: `Raw GWAS Input`,
            mode: "markers",
            type: "scattergl",
            hoverinfo: "text",
            xaxis: "x",
            yaxis: "y",
            marker: { size: 4, color: "#333333", opacity: 0.25 },
          });
        }
      }

      if (plotType === "falcon" || plotType === "overlay") {
        traces.push({
          x: tData.unlinked.x,
          y: tData.unlinked.y,
          text: tData.unlinked.text,
          name: `FALCON (Unlinked)`,
          mode: "markers",
          type: "scattergl",
          hoverinfo: "text",
          xaxis: "x",
          yaxis: "y",
          marker: {
            size: tData.unlinked.sizes,
            symbol: tData.unlinked.symbols,
            color: "#a1a1aa",
            opacity: 0.8,
            line: { width: 1, color: "#71717a" },
          },
        });

        genesToPlot.forEach((g) => {
          const gName = g["GENE"] || g["ID"];
          const color = geneColors[gName];
          if (tData.genes[gName].x.length > 0) {
            traces.push({
              x: tData.genes[gName].x,
              y: tData.genes[gName].y,
              text: tData.genes[gName].text,
              name: `${gName}`,
              mode: "markers",
              type: "scattergl",
              hoverinfo: "text",
              xaxis: "x",
              yaxis: "y",
              marker: {
                size: tData.genes[gName].sizes,
                symbol: tData.genes[gName].symbols,
                color: color,
                line: { width: 1, color: "white" },
              },
            });
          }
        });
      }

      if (hasLD) traces.push(ldTrace);

      let maxY = 0;
      const updateMax = (yArr) => {
        if (yArr && yArr.length > 0) maxY = Math.max(maxY, Math.max(...yArr));
      };
      if (tData.raw) updateMax(tData.raw.y);
      if (tData.unlinked) updateMax(tData.unlinked.y);
      genesToPlot.forEach((g) =>
        updateMax(tData.genes[g["GENE"] || g["ID"]].y),
      );

      const baseClumpY = maxY > 0 ? maxY * 1.05 : 10;
      const clumpYStep = maxY > 0 ? maxY * 0.06 : 1;

      const shapes = [];
      const annotations = [];

      // --- GENE SHAPES ---
      genesToPlot.forEach((g) => {
        const gName = g["GENE"] || g["ID"];
        const color = geneColors[gName];
        const start = parseInt(g["START"]);
        const end = parseInt(g["END"]);
        const centerBP = start + (end - start) / 2;

        shapes.push({
          type: "rect",
          xref: "x",
          yref: "y domain",
          x0: start,
          x1: end,
          y0: 0,
          y1: 1,
          fillcolor: color,
          opacity: 0.1,
          line: { width: 2, dash: "dash", color: color },
        });

        annotations.push({
          x: centerBP,
          y: 0.0,
          xref: "x",
          yref: "y domain",
          text: `<b>${gName}</b>`,
          showarrow: false,
          font: { size: 12, color: color },
          textangle: -45,
          xanchor: "right",
          yanchor: "top",
        });

        const geneHoverText = Object.entries(g)
          .filter(([k, v]) => v != null && v !== "")
          .map(([k, v]) => `<b>${k}</b>: ${v}`)
          .join("<br>");
        traces.push({
          x: [start, end],
          y: [0, 0],
          text: [geneHoverText, geneHoverText],
          name: `${gName} Data`,
          mode: "lines",
          line: { width: 8, color: color },
          hoverinfo: "text",
          showlegend: false,
          xaxis: "x",
          yaxis: "y",
        });
      });

      // --- SMART STACKING CLUMP SHAPES ---
      const clumpTrace = {
        x: [],
        y: [],
        hovertext: [],
        text: [],
        name: "Clumps",
        mode: "lines+markers+text",
        marker: { symbol: [], size: [], color: "#2563eb" },
        line: { color: "#2563eb", width: 2 },
        xaxis: "x",
        yaxis: "y",
        hoverinfo: "text",
        showlegend: false,
      };

      const sortedClumps = Array.from(tData.clumps.entries()).sort(
        (a, b) => a[1].start - b[1].start,
      );
      const occupiedLevels = [];

      sortedClumps.forEach(([clumpId, bounds]) => {
        const { start, end } = bounds;
        let level = 0;
        const buffer = (plotEnd - plotStart) * 0.01;

        while (
          level < occupiedLevels.length &&
          start < occupiedLevels[level] + buffer
        ) {
          level++;
        }
        occupiedLevels[level] = end;

        const currentClumpY = baseClumpY + level * clumpYStep;

        shapes.push({
          type: "line",
          xref: "x",
          yref: "paper",
          x0: start,
          x1: start,
          y0: 0,
          y1: 1,
          line: {
            color: "rgba(107, 114, 128, 0.5)",
            width: 2,
            dash: "dash",
          },
        });
        shapes.push({
          type: "line",
          xref: "x",
          yref: "paper",
          x0: end,
          x1: end,
          y0: 0,
          y1: 1,
          line: {
            color: "rgba(59, 130, 246, 0.5)",
            width: 2,
            dash: "dash",
          },
        });

        const mid = start + (end - start) / 2;
        const hoverStr = `<b>Clump ID:</b> ${clumpId}<br><b>Coordinates:</b> Chr ${chr}:${start.toLocaleString()}-${end.toLocaleString()}<br><b>Length:</b> ${(
          end - start
        ).toLocaleString()} BP`;

        clumpTrace.x.push(start, mid, end, null);
        clumpTrace.y.push(currentClumpY, currentClumpY, currentClumpY, null);
        clumpTrace.marker.symbol.push(
          "triangle-right",
          "circle",
          "triangle-left",
          "circle",
        );
        clumpTrace.marker.size.push(10, 0, 10, 0);
        clumpTrace.hovertext.push(hoverStr, hoverStr, hoverStr, null);
        clumpTrace.text.push("", "", "", null);

        // Preserve ColorManager interaction — assigns the clump a stable
        // palette slot in the shared cache even though this trace is blue.
        // Matches original implicit behavior via ColorManager.getColor().
        getColorForClump(store.caches.clumpColor, clumpId);
      });

      if (clumpTrace.x.length > 0) traces.push(clumpTrace);

      const seabornAxisStyle = {
        gridcolor: "#e5e7eb",
        linecolor: "#e5e7eb",
        tickcolor: "#4b5563",
        tickfont: { color: "#4b5563" },
        titlefont: { color: "#111827", size: 14 },
      };

      const layout = {
        title: `FALCON Zoom & LD Correlation: ${targetGene} Region (Chr ${chr})`,
        plot_bgcolor: "white",
        paper_bgcolor: "white",
        height: 850,
        hovermode: "closest",
        shapes: shapes,
        annotations: annotations,
        legend: { x: 1.02, y: 1 },
        margin: { t: 60, l: 60, r: 20, b: 60 },
        xaxis: {
          ...seabornAxisStyle,
          showgrid: false,
          zeroline: false,
          range: [plotStart, plotEnd],
        },
        yaxis: {
          title: "Negative Log P-Value",
          domain: hasLD ? [0.45, 1] : [0, 1],
          ...seabornAxisStyle,
          showgrid: true,
        },
      };

      if (hasLD) {
        layout.yaxis2 = {
          title: "Correlated BP",
          domain: [0, 0.35],
          ...seabornAxisStyle,
          showgrid: false,
          zeroline: false,
          range: [plotStart, plotEnd],
        };
      }

      console.log(`[LD Debug] Step 10: Complete!`);
      setStatus(`Complete. Unified interactive plots rendered.${overlapWarning}`);

      const result = { data: traces, layout };
      // Side-effect required by the plan: set BEFORE returning.
      store.tdp.lastAnalysis = { data: traces, layout, cfg };
      return result;
    } catch (err) {
      console.error(`[LD Debug] UNCAUGHT ERROR:`, err);
      setStatus(`Error during analysis: ${err.message}`);
      return null;
    }
  }

  return { runAnalysis };
}
