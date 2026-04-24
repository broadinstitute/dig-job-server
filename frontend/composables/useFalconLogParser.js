// frontend/composables/useFalconLogParser.js
// Port of FileLoader.parseLogFile from PEGS/src/dashboard/app.js:114-229.
// Parses a .wg.log with per-chromosome pre-process + Gibbs-iteration timing.

const ITER_COMPONENTS = [
  "Annotation update", "Batched SNP update", "Link Update",
  "Window update", "Gene status update", "Gene effect", "Stats update", "Iter Time",
];

const PRE_PROCESS_KEYS = [
  "Reading sumstats", "Dentist", "Reading S2G", "Reading LD", "RVM",
  "Reading annotations", "Vectorization of region data",
  "Calculating infinitesimal betas", "Stabilization of sparse matrix",
  "Computing SNPs batches", "Computing snp to link variables", "Computing Genes batches",
];

const TIME_RE = /([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s+seconds/i;
const CHR_RE  = /\[Chr\s+([\w]+)\]:/i;

function extractTime(line) {
  const m = line.match(TIME_RE);
  return m ? parseFloat(m[1]) : 0;
}

function parseLogFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const out = {
          data: {},
          preProcess: {},
          chromosomes: new Set(),
          totalTime: "Not Found / Incomplete Run",
        };
        const lines = e.target.result.split("\n");
        let lastChr = null;
        const activePreByChr = {};
        const gibbsStarted = {};

        lines.forEach((line) => {
          const lower = line.toLowerCase();

          if (lower.includes("total time:")) {
            const m = lower.match(/total time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*seconds/i);
            if (m) out.totalTime = parseFloat(m[1]).toFixed(2) + " seconds";
          }

          const chrMatch = line.match(CHR_RE);
          let chr = lastChr;
          if (chrMatch) {
            chr = chrMatch[1];
            lastChr = chr;
            out.chromosomes.add(chr);
            if (!out.data[chr]) {
              out.data[chr] = {};
              ITER_COMPONENTS.forEach((c) => { out.data[chr][c] = []; });
            }
            if (!out.preProcess[chr]) {
              out.preProcess[chr] = {};
              PRE_PROCESS_KEYS.forEach((k) => { out.preProcess[chr][k] = 0; });
            }
          }
          if (!chr || !out.data[chr]) return;

          if (lower.includes("running gibbs")) {
            gibbsStarted[chr] = true;
            activePreByChr[chr] = null;
          }

          if (!gibbsStarted[chr]) {
            // PHASE 1: Pre-processing
            if      (lower.includes("reading sumstats from"))                                activePreByChr[chr] = "Reading sumstats";
            else if (lower.includes("dentist"))                                              activePreByChr[chr] = "Dentist";
            else if (lower.includes("reading s2g"))                                          activePreByChr[chr] = "Reading S2G";
            else if (lower.includes("reading ld") && lower.includes("sparse matrix"))        activePreByChr[chr] = "Reading LD";
            else if (lower.includes("rvm"))                                                  activePreByChr[chr] = "RVM";
            else if (lower.includes("reading annotations"))                                  activePreByChr[chr] = "Reading annotations";
            else if (lower.includes("vectorization of region data"))                         activePreByChr[chr] = "Vectorization of region data";
            else if (lower.includes("calculating infinitesimal betas"))                      activePreByChr[chr] = "Calculating infinitesimal betas";
            else if (lower.includes("stabilization of sparse matrix"))                       activePreByChr[chr] = "Stabilization of sparse matrix";
            else if (lower.includes("computing snps batches"))                               activePreByChr[chr] = "Computing SNPs batches";
            else if (lower.includes("computing snp to link variables"))                      activePreByChr[chr] = "Computing snp to link variables";
            else if (lower.includes("computing genes batches"))                              activePreByChr[chr] = "Computing Genes batches";

            const t = extractTime(lower);
            if (t > 0 && activePreByChr[chr]) {
              out.preProcess[chr][activePreByChr[chr]] = Math.max(
                out.preProcess[chr][activePreByChr[chr]], t
              );
            }
          } else {
            // PHASE 2: Gibbs iteration timings
            const t = extractTime(lower);
            if (t > 0) {
              if      (lower.includes("annotation update"))  out.data[chr]["Annotation update"].push(t);
              else if (lower.includes("batched snp update")) out.data[chr]["Batched SNP update"].push(t);
              else if (lower.includes("link update"))        out.data[chr]["Link Update"].push(t);
              else if (lower.includes("window update"))      out.data[chr]["Window update"].push(t);
              else if (lower.includes("gene status update")) out.data[chr]["Gene status update"].push(t);
              else if (lower.includes("gene effect"))        out.data[chr]["Gene effect"].push(t);
              else if (lower.includes("stats update"))       out.data[chr]["Stats update"].push(t);
              else if (lower.includes("iter time"))          out.data[chr]["Iter Time"].push(t);
            }
          }
        });

        resolve(out);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

export function useFalconLogParser() {
  return { parseLog: parseLogFile, ITER_COMPONENTS, PRE_PROCESS_KEYS };
}
