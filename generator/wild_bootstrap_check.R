# Cross-check of wild_bootstrap_check.py against fwildclusterboot::boottest.
# Usage: Rscript wild_bootstrap_check.R out underpowered
suppressPackageStartupMessages({library(fwildclusterboot); library(sandwich); library(lmtest)})
args <- commandArgs(trailingOnly = TRUE)
outdir <- args[1]; world <- args[2]
files <- sort(list.files(outdir, pattern = paste0("^", world, "_seed.*\\.csv$"), full.names = TRUE))
set.seed(20261112); dqrng::dqset.seed(20261112)
for (f in files) {
  d <- read.csv(f)
  d$unit_f <- factor(d$unit); d$period_f <- factor(d$period)
  fit <- lm(y ~ D + x1 + x2 + unit_f + period_f, data = d)
  ct <- coeftest(fit, vcov = vcovCL(fit, cluster = ~unit, type = "HC1"))["D", ]
  bt <- boottest(fit, param = "D", clustid = "unit", B = 9999,
                 type = "rademacher", impose_null = TRUE)
  cat(sprintf("%s: estimate %.3f, sandwich cluster t %.2f (p %.4f), boottest t %.2f, wild bootstrap p %.4f, 95%% CI [%.2f, %.2f]\n",
              basename(f), ct[1], ct[3], ct[4], bt$t_stat, bt$p_val, bt$conf_int[1], bt$conf_int[2]))
}
