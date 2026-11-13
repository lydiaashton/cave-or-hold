# Independent cross-check of the generator's clustered t and wild cluster bootstrap p,
# written in base R plus sandwich/lmtest (no fwildclusterboot).
# Model: y ~ D + x1 + x2 + unit FE + period FE, clustered by unit (sandwich::vcovCL, HC1).
# Bootstrap: wild cluster, Rademacher weights by unit, null imposed (D coefficient = 0),
# B = 9999, two-sided symmetric p = share of |t*| >= |t|.
# Usage: Rscript wild_bootstrap_base_r.R <out_dir> <world> [seed ...]
suppressPackageStartupMessages({library(sandwich); library(lmtest)})
args <- commandArgs(trailingOnly = TRUE)
outdir <- args[1]; world <- args[2]; seeds <- args[-(1:2)]
files <- sort(list.files(outdir, pattern = paste0("^", world, "_seed.*\\.csv$"), full.names = TRUE))
if (length(seeds)) files <- files[sub(".*_seed([0-9]+)\\.csv$", "\\1", basename(files)) %in% seeds]
B <- 9999

cluster_t <- function(Dt, yt, cl, G, N, K) {
  # FWL on residualized D and y; CR1 small-sample factor as in vcovCL(type = "HC1")
  beta <- sum(Dt * yt) / sum(Dt^2)
  e <- yt - Dt * beta
  s <- rowsum(Dt * e, cl)
  v <- sum(s^2) / sum(Dt^2)^2 * (G / (G - 1)) * ((N - 1) / (N - K))
  c(beta = beta, t = beta / sqrt(v))
}

for (f in files) {
  d <- read.csv(f)
  d$unit_f <- factor(d$unit); d$period_f <- factor(d$period)
  fit <- lm(y ~ D + x1 + x2 + unit_f + period_f, data = d)
  ct <- coeftest(fit, vcov = vcovCL(fit, cluster = ~unit, type = "HC1"))["D", ]

  # Residualize on the controls once (FWL); the bootstrap only changes y.
  Z <- model.matrix(~ x1 + x2 + unit_f + period_f, data = d)
  qz <- qr(Z)
  Dt <- qr.resid(qz, d$D)
  N <- nrow(d); K <- ncol(Z) + 1; cl <- d$unit; G <- length(unique(cl))
  yt <- qr.resid(qz, d$y)
  obs <- cluster_t(Dt, yt, cl, G, N, K)

  # Null imposed: restricted fit omits D; y* = fitted_r + w_g * resid_r.
  ur <- qr.resid(qz, d$y)            # restricted residuals (controls only)
  fr <- d$y - ur
  set.seed(20261113)
  units <- sort(unique(cl)); idx <- match(cl, units)
  tstar <- numeric(B)
  for (b in seq_len(B)) {
    w <- sample(c(-1, 1), length(units), replace = TRUE)[idx]
    ys <- fr + w * ur
    tstar[b] <- cluster_t(Dt, qr.resid(qz, ys), cl, G, N, K)["t"]
  }
  p_boot <- mean(abs(tstar) >= abs(obs["t"]))
  cat(sprintf("%s: estimate %.3f, sandwich cluster t %.2f (p %.4f), FWL t %.2f, wild bootstrap p %.4f\n",
              basename(f), ct[1], ct[3], ct[4], obs["t"], p_boot))
}
