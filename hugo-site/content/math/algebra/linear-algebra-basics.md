---
title: "선형대수 기초 정리"
date: 2026-02-19T09:00:00+09:00
categories: ["math", "algebra"]
tags: ["linear-algebra", "eigenvalue", "svd"]
math: true
---

## 1. 고유값 분해

정방 행렬 $A \in \mathbb{R}^{n \times n}$가 대각화 가능할 때:

$$
A = P \Lambda P^{-1}
$$

여기서 $\Lambda = \text{diag}(\lambda_1, \ldots, \lambda_n)$은 고유값 행렬, $P$는 고유벡터 행렬이다.

## 2. 특이값 분해 (SVD)

임의의 행렬 $A \in \mathbb{R}^{m \times n}$에 대해:

$$
A = U \Sigma V^T
$$

- $U \in \mathbb{R}^{m \times m}$: 좌 특이벡터 (직교 행렬)
- $\Sigma \in \mathbb{R}^{m \times n}$: 특이값 대각 행렬
- $V \in \mathbb{R}^{n \times n}$: 우 특이벡터 (직교 행렬)

## 3. 양정치 행렬

대칭 행렬 $A$가 **양정치(positive definite)**라 함은:

$$
x^T A x > 0, \quad \forall x \neq 0
$$

양정치 행렬의 모든 고유값은 양수이다: $\lambda_i > 0$.
