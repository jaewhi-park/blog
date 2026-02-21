---
title: "Wigner의 반원 법칙"
date: 2026-02-21T09:00:00+09:00
categories: ["math", "probability"]
tags: ["random-matrix", "wigner", "semicircle-law"]
math: true
llm_generated: true
llm_disclaimer: true
llm_model: "claude-sonnet-4-20250514"
---

{{< disclaimer >}}

## 1. 서론

Random Matrix Theory(RMT)의 가장 기본적인 결과 중 하나인 **Wigner의 반원 법칙(Semicircle Law)**을 살펴본다.

## 2. 설정

$n \times n$ 실대칭 행렬 $W_n$을 다음과 같이 정의한다:

$$
W_n = \frac{1}{\sqrt{n}} X_n
$$

여기서 $X_n = (X_{ij})$는 독립(대각선 위)인 확률변수들로 이루어진 대칭 행렬이다.

각 성분은 다음을 만족한다:
- $\mathbb{E}[X_{ij}] = 0$
- $\mathbb{E}[X_{ij}^2] = 1$ (대각선 위, $i < j$)

## 3. 경험적 스펙트럼 분포

$W_n$의 고유값을 $\lambda_1 \leq \lambda_2 \leq \cdots \leq \lambda_n$이라 하면, **경험적 스펙트럼 분포(ESD)**는:

$$
\mu_n = \frac{1}{n} \sum_{i=1}^{n} \delta_{\lambda_i}
$$

## 4. Wigner의 반원 법칙

**정리 (Wigner, 1958).** $n \to \infty$일 때, $\mu_n$은 반원 분포 $\mu_{sc}$로 약수렴한다:

$$
d\mu_{sc}(x) = \frac{1}{2\pi} \sqrt{4 - x^2} \, \mathbf{1}_{|x| \leq 2} \, dx
$$

이 분포의 지지(support)는 $[-2, 2]$이며, 밀도 함수는 반원 형태를 띤다.

## 5. 모멘트 방법 증명 스케치

증명의 핵심은 **모멘트 방법**이다. $k$-차 모멘트를 계산하면:

$$
\int x^k \, d\mu_n(x) = \frac{1}{n} \text{tr}(W_n^k) = \frac{1}{n^{1+k/2}} \sum_{i_1, \ldots, i_k} \mathbb{E}[X_{i_1 i_2} X_{i_2 i_3} \cdots X_{i_k i_1}]
$$

$n \to \infty$에서 이 값은 **카탈란 수(Catalan number)** $C_{k/2}$ ($k$ 짝수)로 수렴한다:

$$
C_m = \frac{1}{m+1} \binom{2m}{m}
$$

이는 정확히 반원 분포의 모멘트이다.

## 6. 참고 문헌

- Wigner, E. P. (1958). On the distribution of the roots of certain symmetric matrices.
- Anderson, G. W., Guionnet, A., & Zeitouni, O. (2010). *An Introduction to Random Matrices*.
