---
title: "Free Probability 입문"
date: 2026-02-20T09:00:00+09:00
categories: ["math", "probability"]
tags: ["free-probability", "voiculescu"]
math: true
llm_assisted: true
llm_disclaimer: true
llm_model: "claude-sonnet-4-20250514"
---

{{< disclaimer >}}

## 1. 소개

**Free Probability**(자유 확률론)는 Voiculescu가 1980년대에 도입한 비가환 확률론의 한 분야다. 고전 확률론에서의 독립성(independence) 개념을 **자유 독립성(free independence)**으로 대체한다.

## 2. 비가환 확률 공간

비가환 확률 공간은 쌍 $(\mathcal{A}, \varphi)$로 정의된다:

- $\mathcal{A}$: 단위원을 가진 대수(algebra)
- $\varphi: \mathcal{A} \to \mathbb{C}$: 선형 범함수 ($\varphi(1) = 1$)

고전 확률론에서 확률변수의 기대값에 대응하는 것이 $\varphi$이다.

## 3. 자유 독립성

부분대수 $\mathcal{A}_1, \mathcal{A}_2 \subset \mathcal{A}$가 **자유(free)**하다는 것은 다음을 의미한다:

$$
\varphi(a_1 a_2 \cdots a_n) = 0
$$

단, $a_j \in \mathcal{A}_{i_j}$, $\varphi(a_j) = 0$, 인접한 $i_j \neq i_{j+1}$.

이는 고전 독립성의 조건 $\mathbb{E}[XY] = \mathbb{E}[X]\mathbb{E}[Y]$와 근본적으로 다른 구조를 갖는다.

## 4. Free Central Limit Theorem

고전 CLT에서 독립인 확률변수의 합이 정규분포로 수렴하듯, 자유 독립인 변수의 합은 **반원 분포**로 수렴한다:

$$
\frac{a_1 + a_2 + \cdots + a_n}{\sqrt{n}} \xrightarrow{d} \mu_{sc}
$$

이것이 바로 Wigner의 반원 법칙과 Free Probability를 연결하는 핵심이다.
